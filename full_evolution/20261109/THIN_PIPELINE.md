# WRD58 简化管道与模型替换实验

主方法依据 `pipeline.py` 与 `research/workflow/stages.py`。本分支是独立实验入口。每个阶段由同一个指定模型在固定原生 OpenClaw 2026.9.5 内完成，宿主只投递、移交实际文件、核对终态和记账。每个模型用相同的三段提示、材料、阶段边界和预算。保留全量演化集原件及已冻结评估边界。

## 从原管道保留什么

| 阶段 | 模型拿到什么 | 产出与接续 |
| --- | --- | --- |
| `route` 路线筛选 | 完整历史索引、会话、已有附件。制作和独立验收答案都不可见 | 写 `outputs/route.json`，给出实际来源、用户纠正、范围与适用边界。`MAKE` 进入制作，有据 `STOP` 或 `BLOCKED` 结束并保留证据 |
| `make` 制作与试跑 | 原历史、资源、本臂自己写出的路线卡 | 形成轻量 `SKILL.md` 及必要脚本/模板/资料。按公开用法真实执行，利用工具返回自行修复。提交 `outputs/evidence/decision.json` 和试跑证据。制作已结束、实际有候选但漏写决定时，保留其未完成状态，复验仍可按实物补齐结论 |
| `check` 复验与局部修订 | 同一来源、本臂路线卡、实际候选原件与制作阶段已有证据 | 新的原生会话按公开用法复验。已合格的候选保留原字节。有具体失败时最多一轮局部修订，修改落进最终包后再实际跑。记录 `KEEP`／`STOP`／`BLOCKED` 与可核验的版本证据 |

`route → make → check` 恢复了原管道的路线、制作和真实反馈交接。原流程的独立任务检索、业务有／无技能配对与价值评审分列在下一实验，先看制作器本身能否交付可用工件。宿主根据完整终态做整任务移交，不在原生会话中注入单步指令、不替模型执行工具或修代码、不把 JSON 自述当作试跑成功。`check` 是同一臂的复验机会，独立质量评审仍看最终实物与冻结验收。

用户报告后续单会话批次有提高回复上限、抑制复读和扩大请求预算的试验，也报告了脚本语法错误、未修复与终态丢失。完整回包仍待审查。这里保留分任务、真实失败反馈、一次局部修订和新会话收尾来验证能否减少上述失败。旧 4096 批次和后续报告均作为既有证据留存。

## 对照与结论

- **训练净增益**比较 `wrd58-14b-241` 与 `wrd58-14b-0`，同一套管道，各自写路线及后续工件。两臂用相同的 Spark v2 服务和同尺寸基座。
- **逼近大模型**将 `glm-5.3-flash` 放入同样的简化管道。GLM 原生产管道的 29 个保留技能和历史使用结果只作背景。三臂的同来源配对回答现时能力差距。业务使用的 TSR、论文五维 Q 和使用减负须在合格包上另做固定执行器的配对试用。
- **先开发后盲验。** 现有 `auto01`–`auto04` 已经见过模型结果，只作配对开发回归。先跑一个既有正向案例，再按相同提示跑四组。正式结论使用新冻结的独立来源组，排除本批、历史已见与训练血缘，原 226 不反哺训练。所有候选由独立评审盲评，错停止、空包、已截断、实质缺陷、不可观测设施错误分别统计。正确停止单列。
- **主要指标。** 事前以独立来源组为分母，报告真实合格制作率、`STOP` 正确性、共同可评分组的制作 Q、全部实际 tokens／请求／墙钟、每合格技能总成本。制作 Q 的五维是来源忠实、流程可执行、资源自足、验证修订可靠、封装易用。命令临时回退而最终包未改，不能计技能修订成功。建议盲验前将“逼近”定义为合格率较 GLM 至多低 10 个百分点、共同可评分组的制作 Q 平均至多低 5 分、无严重虚报或误拒。应同时报配对不确定性。成本独立报告，训练贡献仍用 241 对 0 估计。四组开发回归只回答是否值得扩展，这些阈值是建议的工程判断线。

## 运行边界

Spark 提供 Qwen3-14B v2 的 0／241 服务，x86 工具主机用 Python 3.11+、Git、Docker 和固定的 `linux/amd64` OpenClaw 镜像。GLM 可由工具主机访问既有 OpenAI 兼容端点。GLM 与 Spark 可能使用不同服务实现和分词器，记录可核验实际配置。GLM 端点必须支持原生消息、完整工具 schema、流式工具调用和计量，不能仅用配置声明代替实际证据。

| 阶段 | HTTP 请求上限 | 单回复上限 | 累计 completion 上限 | 任务时间上限 |
| --- | ---: | ---: | ---: | ---: |
| 路线 | 12 | 8192 | 32768 | 1800 秒 |
| 制作 | 48 | 32768 | 98304 | 5400 秒 |
| 复验与修订 | 36 | 16384 | 65536 | 3600 秒 |

completion 含推理。每阶段的累计额度和请求数同时生效，满额保守预留和未知用量单列。最多 96 请求、3 小时原生会话时间为三段上限之和，未进入阶段不消耗额度。一次提交不自动加预算。不同模型均走同一原生工具接口和阶段契约，原生系统中按模型身份产生的元数据照常留证。后续更改推理参数须重新绑定配置，不能混报为同批。

## 获取材料

在工具主机上运行。已恢复的演化集可以直接用绝对路径指向，无需重解包。首次获取继承既有 54 个分卷，无 AES 密钥依赖。Windows 工具主机把 `python3` 换为 `python`，使用 Windows 路径。固定镜像恢复见 [OpenClaw 镜像说明](../../OPENCLAW_RESTORE.md)。

```bash
git clone --depth 1 --single-branch --branch codex/wrd58-thin-pipeline \
  https://github.com/jiaotangbuding177/WRD_dataset.git wrd58-thin
cd wrd58-thin/full_evolution/20261109
export CORPUS="$PWD/corpus"
python3 tooling/restore_corpus58.py --delivery DELIVERY.json --out "$CORPUS"
```

Spark 继续使用已验证的 v2 权重和 vLLM 启动配置。用既有 [`serve_wrd58.sh`](execution/spark/serve_wrd58.sh) 启动 `14b yarn128 0,241`，或继续用已在同一服务实例验证两别名的配置。保留实际启动命令、配置和日志。后续批次的重复惩罚以其真实服务日志确认，不根据口头摘要写入。工具主机私有链路映射 `127.0.0.1:18758`，原生中继独占 18759。两个端口的用法见 [上轮环境交接](AUTONOMOUS.md)。

GLM 的端点身份用仓库和回包目录之外的权限受控 JSON 配置。`model` 为 `glm-5.3-flash`，`base_url` 为已授权的 OpenAI 兼容 `/v1` 地址，`api_key` 为现有端点的凭据，`context_window` 与 `max_tokens` 填该路由可支持的值。保留传输和用量回执，凭据不参与归档。GLM 与 Spark 无需放在同一物理机器。

## 启动首例和收集回包

以下在工具主机仓库的 `full_evolution/20261109` 执行。`$CORPUS` 指实际恢复目录。`$SPARK_LOG` 指 Spark 原启动回执，例如 `receipts/serve_14b_128k.log`。`$GLM_CREDENTIALS` 指仓库外的私有 JSON。

```bash
python3 execution/local/run_thin58.py verify \
  --corpus "$CORPUS" --delivery DELIVERY.json --selection autonomous/selection/selection.json

python3 execution/local/run_thin58.py pair --case auto01 --size 14b \
  --corpus "$CORPUS" --delivery DELIVERY.json --selection autonomous/selection/selection.json \
  --startup-log "$SPARK_LOG" --include-glm --glm-credentials "$GLM_CREDENTIALS" \
  --runs thin-runs
```

PowerShell 使用同一个入口，按实际路径设置变量。

```powershell
$corpus = Join-Path (Get-Location) 'corpus'
$sparkLog = 'receipts/serve_14b_128k.log'
$glmCredentials = 'C:/private/wrd-glm.json'
python execution/local/run_thin58.py verify --corpus $corpus --delivery DELIVERY.json --selection autonomous/selection/selection.json
python execution/local/run_thin58.py pair --case auto01 --size 14b --corpus $corpus --delivery DELIVERY.json --selection autonomous/selection/selection.json --startup-log $sparkLog --include-glm --glm-credentials $glmCredentials --runs thin-runs
```

Spark 先行时省略 `--include-glm --glm-credentials "$GLM_CREDENTIALS"`。GLM 单独运行用 `run --case auto01 --arm glm-5.3-flash --glm-credentials "$GLM_CREDENTIALS"`，附同一组 `--corpus`、`--delivery`、`--selection`、`--runs`。同一模型和案例已经有终态时，沿用完整记录。发生未闭合派发时先保全原回执。第一次对照使用默认复验阶段，后续四组开发回归去掉 `--case auto01`。`prepare` 加 `--case auto01 --arm wrd58-14b-241 --runs thin-runs` 可只构建路线阶段工作区，附相同材料参数，无推理。

```bash
python3 execution/local/package_thin58.py --runs thin-runs \
  --selection autonomous/selection/selection.json --receipts receipts \
  --out wrd58-thin-return.zip
```

回传 `wrd58-thin-return.zip` 和 `wrd58-thin-return.zip.sha256`。若需归档多个主机的运行，分别带回 ZIP 与 SHA，所有启动日志与失败账本保留。接收方核对阶段终态和最终候选，按 `autonomous/selection/EVALUATOR_ONLY.md` 中的独立输入与范围验收。本轮试验结果的候选选中记录、各阶段实际工具及原始响应均包含于回包。

## 已完成验证

四组演化来源的本机 CPU 材料校验通过，三臂路线阶段初始文件和 Git 树一致。模拟后端验证了原生工作区绑定声明、阶段之间的字节交接、漏写决定时的复验、原包复验与修订包复验、正确停止、设施故障留账和断点不重复派发。回包程序验证了阶段索引、成员 SHA 及 ZIP sidecar。实际 GLM 端点协议和真实产出需要首轮运行确认。本轮模型调用和训练为零。[CPU 核验回执](execution/local/RUN_THIN58_CPU_CHECK.json)
