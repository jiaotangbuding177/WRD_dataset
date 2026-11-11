# 复用 1,107 条会话的历史路线，让 14B-241 制作和试用技能

原 WRD 已筛完 1,107 条会话，留下 121 条归并后的工作路线。本入口固定这些路线的原 ID、范围、适用条件和来源，让 v2 `wrd58-14b-241` 从制作开始执行。路线来源、历史处置和新结果分别记账。原生 OpenClaw 负责会话、工具和技能发现。

## 从哪里开始

- `route_data/SOURCE_DECISIONS.json` 覆盖 1,107 条来源。`route_data/ROUTES.json` 有 121 条路线，29 条曾保留、60 条候选、13 条待修、19 条拒绝。前 102 条可排制作，19 条拒绝保留历史处置。既有 29 个成品技能的正文及历史试用输出均留在旧库。
- `route_data/TRIALS.json` 为 48 条路线冻结了各一个历史真实试用任务。它们从 389 个历史配对中筛得，有相同委托及附件的原始回执，试用输入与该路线制作来源及附件隔离。排除原 226 及额外冻结效果集。部分试用任务曾出现在其他历史路线中，结果按路线级历史试用解释。另 54 条路线可以制作和功能复验，待有独立同类试用材料后再确认入库。
- 试用资料只交付原委托、相应输入和哈希。41 个附加对象和已发布语料对象共同还原 54 个文件挂载。`route_data/EXPORT_RECEIPT.json` 保留核对口径与来源证据。

## 模型怎么走后半段

1. **制作。** 给 241 已归并的路线卡、实际会话和附件。它写 `outputs/skill/SKILL.md` 和包内资源，按公开用法试跑，保存实际命令和工件。预算内出现局部故障时修对应文件并复跑。已有候选但制作收尾失败的记录一并交给下一阶段检查。
2. **独立复验。** 新原生会话读取候选，实际运行包内公开入口。复验用例、功能结果和匹配的原生工具回执均须可核验。修订必须进入最终包，并用触发失败的材料重跑。缺真实验证证据时只保全候选。
3. **成对试用。** 同一条历史业务委托、相同附件、同一个模型和同预算在两个新原生工作区各跑一次。技能组只有该版本技能经 OpenClaw 原生发现。验证实际阅读、使用与交付，计入全部模型请求及 tokens。两臂的业务产物交给单独的审核会话，工件用 A/B 标号。
4. **修订和交付。** 有证据的可定位业务缺陷回传给一次新修订会话，修订版先复验，再重跑技能试用并重新审核。已有条件匹配的无技能臂按原回执复用。正式交付要求真实功能复验、两臂均完成、技能组确实使用技能资源、tokens 和请求数双降。纯文本技能也可以参加试用，缺少可自动核实的使用证据时留待人工核对。合格新包进入运行目录的 `qualified`，旧库无需迁移。

这次固定 GLM 历史路线，只衡量 **14B-241 能否接手制作、修订、试用和审核**。比较训练增益时，可给 `wrd58-14b-0` 相同的路线和试用合同。使用 `glm-5.3-flash` 对照时为相同后半段。当前 241 权重与部分历史来源重合，结果登记为历史重放。

## 交给同事的运行命令

Spark 启动 v2 `14b yarn128 0,241` 服务，使用已核对的适配器和启动日志。x86 工具主机使用固定 OpenClaw 2026.9.5 镜像，把已授权的 Spark 私有链路映射到本机 `127.0.0.1:18758`。本机 18759 由原生中继独占。模型启动和连通步骤见 [THIN_PIPELINE.md](THIN_PIPELINE.md)，镜像恢复见 [OPENCLAW_RESTORE.md](../../OPENCLAW_RESTORE.md)。模型凭据放在运行目录和回包之外。

```bash
set -eu
git clone --depth 1 --single-branch --branch codex/wrd58-reused-routes \
  https://github.com/jiaotangbuding177/WRD_dataset.git wrd58-reused-routes
cd wrd58-reused-routes/full_evolution/20261109
CORPUS="${CORPUS:-$PWD/corpus}"
if [ ! -f "$CORPUS/INDEX.jsonl" ]; then
  python3 tooling/restore_corpus58.py --delivery DELIVERY.json --out "$CORPUS"
fi
python3 execution/local/run_reuse58.py verify --corpus "$CORPUS" --delivery DELIVERY.json

run_status=0
python3 execution/local/run_reuse58.py run --corpus "$CORPUS" --delivery DELIVERY.json \
  --route shareholder-register-compile --arm wrd58-14b-241 \
  --startup-log "${SPARK_LOG:?set SPARK_LOG to the verified Spark log}" --runs reuse-runs || run_status=$?

if [ -d reuse-runs ]; then
  python3 execution/local/package_thin58.py --runs reuse-runs \
    --selection route_data/ROUTES.json --out wrd58-reused-routes-return.zip
fi
exit "$run_status"
```

首条采用 `shareholder-register-compile`，它有可归并的历史路线、明确的表格交付和冻结试用任务。收到阶段回执后可以重复 `--route` 指定多条路线，或用 `--all` 调度 102 条未拒绝路线。用 `prepare` 替换 `run` 可只准备制作输入。Windows 上将 `python3` 换为 `python`，使用对应绝对路径。

返回 `wrd58-reused-routes-return.zip` 和 `.sha256`。同一运行目录可以继续，已有请求和结果按 SHA 复用。未知派发保留原位以核对回执。每条路线的终态在 `reuse-runs/<路线>/<模型>/attempt-001/receipt.json`，通过全部准入的包在同一路线和模型目录的 `qualified/attempt-001/skill/`。
