# WRD58 自主技能沉淀实验

从原始会话和可用附件开始，验证 v2-241 是否学会识别复用机会、用原生工具制作和修订技能，并降低每个合格技能的耗时及成本。一个案例臂只有一个初始委托和一段固定 OpenClaw 会话。会话内可以有多次原生工具调用。模型自己决定何时查证、试跑、修订或停止。

## 首批做什么

- 4 个独立来源组、5 条已冻结会话。覆盖可执行技能制作、历史用户纠正、跨来源复用及有据停止。以来源组计独立样本。4 组 × 14B-0／14B-241 为 8 个原生会话。8B-0／8B-241 是相同合同的可选第二组。
- 只用 `training-v2-run` 的 checkpoint-0 和 checkpoint-241。既有 exact parity 支持 checkpoint-0 作同尺寸基座对照。相同原文、附件、镜像、原生工具、启动配置和预算，同尺寸内交替臂顺序。训练影响看同源 241 对 0。历史 GLM 的 29 个保留技能及成本账本作为历史参照。只有将 GLM 另接入同一自主任务并取得同范围交付，才能算与 GLM 的配对差距。首批执行命令没有原 GLM 管道入口。
- 质量同时看来源忠实、正确停止、可用文件、公开命令和试跑证据。实际候选位于 `outputs/skill/`，短终态写入 `outputs/evidence/decision.json`。终态状态为 `KEEP`、`STOP` 或 `BLOCKED`。会话结束后独立评分，审查侧不向模型发送下一轮修复提示。
- 单臂最多 24 次模型 HTTP 请求、4096 tokens 单回复、32768 tokens 累计 completion（含推理）和 3600 秒。输入正文、固定工具目录与原生历史另行计量。未回报用量按原保守预留记录，和实测分开。新入口支持从已有终态接着跑其他臂，已派发但未得终态的编号保留作待核证据。

## 同事启动命令

**两机分工。** Spark ARM64 运行 vLLM 和已训练权重。原生工具主机运行现有的 `linux/amd64` OpenClaw 2026.9.5 镜像，准备 Python 3.11+、Git、Linux Docker 容器。镜像恢复沿用 [固定镜像手册](../../OPENCLAW_RESTORE.md)。已有环境可跳过导入。工具机须能通过同事现有私有链路访问 Spark 的 18758。给工具主机映射为 `127.0.0.1:18758`。18759 留给该次原生执行的独占中继。运行包没有模型权重和 Docker 镜像的副本。

### 1. 获取仓库与演化集

在工具主机的 Bash 中执行。已有校验通过的演化集时，`CORPUS` 直接设成其绝对路径，跳过 restore。首次检出沿用父版本 54 个普通 Git 二进制分卷，约 900 MB，不需要 AES 或 Git LFS 恢复该演化集。

```bash
git clone --depth 1 --single-branch --branch codex/wrd58-autonomous-native \
  https://github.com/jiaotangbuding177/WRD_dataset.git wrd58-autonomous
cd wrd58-autonomous/full_evolution/20261109
export CORPUS="$PWD/corpus"
python3 tooling/restore_corpus58.py --delivery DELIVERY.json --out "$CORPUS"
python3 execution/local/run_autonomous58.py verify \
  --corpus "$CORPUS" --delivery DELIVERY.json --selection autonomous/selection/selection.json
```

Windows 工具主机可在 PowerShell 使用下列命令。假定仓库已按上一步 clone。

```powershell
Set-Location wrd58-autonomous/full_evolution/20261109
$corpus = Join-Path (Get-Location) 'corpus'
python tooling/restore_corpus58.py --delivery DELIVERY.json --out $corpus
python execution/local/run_autonomous58.py verify --corpus $corpus --delivery DELIVERY.json --selection autonomous/selection/selection.json
```

### 2. 在 Spark 启动 14B-0 和 14B-241

Spark 侧只需取得同一分支的已有 `full_evolution/20261109/execution/spark/serve_wrd58.sh`。在仓库根执行。已有 v2 权重和 Hugging Face 缓存的机器用原值。若训练容器挂载不能自动识别，在 shell 先设置 `WRD_WORKSPACE_ROOT` 为包含 `out58_14b_v2` 的绝对路径，`WRD_HF_ROOT` 为包含 `hub/` 的绝对路径。使用同事已验证的 ARM64 vLLM 镜像，若不是脚本默认镜像，以 `WRD_VLLM_IMAGE` 传本机镜像名或 ID。脚本检查基座 revision 与两个 adapter SHA，启动时记录实际镜像与配置。

```bash
set -o pipefail
mkdir -p wrd58-receipts
bash full_evolution/20261109/execution/spark/serve_wrd58.sh 14b yarn128 0,241 \
  2>&1 | tee wrd58-receipts/serve_14b_128k.log
```

保持服务运行，把 `serve_14b_128k.log` 复制到工具主机的 `full_evolution/20261109/receipts/`。保留已有私有链路。若工具主机和 Spark 可经 SSH 直连，示例是 `ssh -N -L 127.0.0.1:18758:127.0.0.1:18758 user@spark-private-host`。使用实际用户名和地址。模型列表验证只读，不发推理。

### 3. 从工具主机一次派发两臂并打包

在 `full_evolution/20261109` 执行。

```bash
mkdir -p receipts
python3 execution/local/run_autonomous58.py pair --size 14b \
  --corpus "$CORPUS" --delivery DELIVERY.json --selection autonomous/selection/selection.json \
  --startup-log receipts/serve_14b_128k.log --runs autonomous-runs-14b

python3 execution/local/package_corpus_return58.py \
  --runs autonomous-runs-14b --selection autonomous/selection/selection.json \
  --receipts receipts --out wrd58-autonomous-14b-return.zip
```

PowerShell 等价命令如下。

```powershell
New-Item -ItemType Directory -Path receipts -Force | Out-Null
python execution/local/run_autonomous58.py pair --size 14b --corpus $corpus --delivery DELIVERY.json --selection autonomous/selection/selection.json --startup-log receipts/serve_14b_128k.log --runs autonomous-runs-14b
python execution/local/package_corpus_return58.py --runs autonomous-runs-14b --selection autonomous/selection/selection.json --receipts receipts --out wrd58-autonomous-14b-return.zip
```

默认运行 4 组。若只需有意先做一个真实案例，在 `pair` 命令追加 `--case auto01`，之后用原运行目录执行全批，保全已有终态。要核查投递树时，可用同一入口的 `prepare --case auto01 --arm wrd58-14b-241 --runs autonomous-runs-14b`，附相同的 `--corpus`、`--delivery`、`--selection`。`verify` 与 `prepare` 只核资源和投递，不消耗模型额度。可选 8B 使用 `8b` 与相应日志和独立运行目录，先按已有办法结束本次 14B 服务再切换。

## 回传与结论口径

回传 `wrd58-autonomous-14b-return.zip` 和 `wrd58-autonomous-14b-return.zip.sha256`。包内保留实际 `outputs/skill/`、原生原始会话、工具请求与返回、初始资源绑定、预算、模型请求与响应、启动日志和失败证据。若执行只跑了部分，仍按原样带回。用 `execution/local/audit_autonomous58.py` 做只读证据核验。独立评分使用 `autonomous/selection/` 的评分材料，评估工件前核对版本 SHA，不把评分内容投给模型。可执行候选只在隔离环境试验。

```bash
python3 execution/local/audit_autonomous58.py --archive wrd58-autonomous-14b-return.zip \
  --selection autonomous/selection/selection.json --size 14b --out wrd58-autonomous-14b-audit.json
```

同源分别报告 241/0 的制作合格数、正确停止数、可观察的修订链、墙钟、实际及未知用量。全成本计模型、设备、工具、返工和实际人工，分母为去重合格技能数。另报每正确处理来源组的成本，体现停止和复用的价值。两组都无合格技能时单位成本不可计算。首批为工程判断，完整生产准入和实际使用减负仍要另看真实业务试用证据。

## 已核验范围

用全量本地实物及同事交回的恢复目录核对所选材料，4 组 × 4 臂共 16 份 Git 工作区通过 CPU 准备检查。同组初始文件与树一致，首轮只显式枚举索引，评分材料未进入工作区。回包审计通过 3 项 CPU 回归。完整记录见 [启动器核验](execution/local/AUTONOMOUS_CPU_CHECK.json) 和 [材料血缘核验](autonomous/selection/STATIC_VERIFICATION.json)。本轮没有启动 Spark 推理，实际生成质量与两机私有链路待本次运行留证。
