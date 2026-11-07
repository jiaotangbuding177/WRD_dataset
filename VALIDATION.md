# WRD58 v2 技能生成验证

当前任务只验证小模型作为 WRD 技能制作 Agent 的表现。输入是原会话、可用资源、制作目标和预算；输出是 `outputs/skill/`、制作内试跑、修订版本和终态证据。模型通过固定 OpenClaw 原生工具自主执行整个制作过程。用户于 2026-11-07 明确将独立业务消费延期，本文件覆盖旧交接中的消费安排。

本文件从训练和离线选模完成处接续。验收 18/18、两组 checkpoint-0 基座一致性和 144 条短探针已经归档。只用 v2 的 0/26 检查点。[离线筛查提交](https://github.com/jiaotangbuding177/WRD_dataset/commit/4af0c4f1190a595d5b243026aaa68e7026ab0f17)

| 臂 | 角色 | adapter SHA256 |
|---|---|---|
| `wrd58-8b-0` | 8B 基座对照 | `27fb78e716391ef21bb3255fa00846e32e021bc2801f7d3391a73f62d84bbb47` |
| `wrd58-8b-26` | 8B 入围 | `2442a2e8f2dad2d5bdd88b0f4e054064548f28023246ea80473e46ddbc7dd786` |
| `wrd58-14b-0` | 14B 基座对照 | `a82c0cd548758be31f603d0f6b156f6ef57178363277bead42581e5df85a7512` |
| `wrd58-14b-26` | 14B 入围 | `81d2d09784f6d4239f9dd0fb1fa3b99930966e01d78d5c5f949c123f191d1792` |

两组的 26 都是 contract 阶段终点，这轮比较这两个候选相对同尺寸基座的完整技能制作行为。过程课程检查点 80/134/188/241 仍保留，当前四臂结果只归属于实际受测检查点，后续如比较过程课程，同样使用技能生成任务。Spark 使用冻结 Qwen3-8B `b968826d9c46dd6066d109eabc6255188de91218` 与 Qwen3-14B `40c069824f4251a91eefaf281ebe4c544efd3e18`。Spark 每次载入一个尺寸，在同一服务同时暴露该尺寸的两臂。

## A. 一次准备并验通两尺寸

1. 先按 [OpenClaw 恢复](OPENCLAW_RESTORE.md) 在与 Spark 能建立受控连接的 **x86_64** 主机导入固定 `linux/amd64` 镜像。该主机持有工作区与受控 DEV 材料。ARM64 Spark 负责 vLLM。确认 x86 主机上的 Docker 容器可以通过本地 relay 访问模型接口。Windows 到 Spark 的人工逐包交接只用于合成诊断，耗时单列。已有同配置通过的回执可复用，避免重复验机。
2. 在 Spark 的包根目录执行以下命令。终端 A 持续运行服务，终端 B 运行验收脚本。先执行 8B，完成对应的两臂原生烟测后停止该服务，再用 `14b` 替换命令中的 `8b`。保存两尺寸启动日志、服务镜像 ID 和验收 JSON。

   ```bash
   mkdir -p receipts
   bash spark/serve_wrd58.sh 8b yarn128 2>&1 | tee receipts/serve_8b_128k.log
   ```

   ```bash
   python3 spark/smoke_wrd58.py 8b --context 131072 --long-input --out receipts/smoke_8b_128k.json
   ```

   Spark 启动日志须记录对应的固定基座 revision、两个 adapter SHA、`yarn128`、`model_length=131072` 及镜像 ID。两尺寸用同一个 vLLM 镜像。`smoke_*_128k.json` 须为 `pass`。两臂都须能输出合法结构化工具调用和流式用量，并实际接受至少 65,806 输入 tokens 与请求的 32,768 输出预算。原先 8B 单请求回包使用约 31K 输入，只是接口实证。
3. 每个尺寸验收后，把该尺寸的日志和 JSON 放在 x86 包内 `local/spark_receipts/`。保持该尺寸服务在线，在 x86 包根目录运行它的 `doctor` 和两条 `smoke`。两个尺寸共四个 Spark 文件、四条原生 `smoke` 都齐全后才进入 B。

   ```bash
   # Spark 当前在线 8B 时
   python3 local/run_native58.py doctor --arm wrd58-8b-0 --profile yarn128
   python3 local/run_native58.py smoke --arm wrd58-8b-0 --profile yarn128 --attempt 1
   python3 local/run_native58.py smoke --arm wrd58-8b-26 --profile yarn128 --attempt 1
   # Spark 当前在线 14B 时
   python3 local/run_native58.py doctor --arm wrd58-14b-0 --profile yarn128
   python3 local/run_native58.py smoke --arm wrd58-14b-0 --profile yarn128 --attempt 1
   python3 local/run_native58.py smoke --arm wrd58-14b-26 --profile yarn128 --attempt 1
   ```

   原生烟测每臂 300 秒、最多 8 个模型 HTTP 请求、单次输出最多 1,024 tokens。`local/runs/smoke-yarn128-<arm>-01/smoke_result.json` 须全项 `PASS`。它检查原生完整读合成 `SKILL.md`、真实 `exec`、正确文件 `outputs/result.json`（`sum=42` 与 `proof=native_exec`）、下一模型请求含工具结果、完整原生工具配置、结构化调用、thinking、实际用量和请求身份。这是合成工具接线验机，不纳入业务消费或技能生成效果统计。失败时保留原尝试并写原因。确认修复后以新 `--attempt` 单次执行，保留旧耗时与用量。

## B. 先做一组四臂制作

正式 DEV 共冻结四个来源。当前可直接投递 EDU 文本组 `conv_497a2363eddb`，范围限定对外短文技能制作。`LEGAL` 组缺原协议和承诺函，`BIZ` 组缺原招标文件和投标成品，`OFFICE` 组缺原 PNG 序列和大纲。三组记 `HOLD_ORIGINAL_MATERIALS`。本次四臂均从同一完整文本会话开始。补齐缺件核来源与 SHA 后，再按同一制作协议扩展；原 226 来源与正式 TEST 继续隔离。

从授权私有路径取得原冻结 `local_materials/`。本轮只需 `DEV_MATERIALS.json` 及其中 maker 对应的制作源与提示。旧 ZIP 内两道消费简报留档，不校验、不投递、不执行。Git 包提供启动器、配置与合成诊断资源。当前 EDU 原始源为 62,997 字节，SHA256 为 `adf496e34aa109450dcf4c1ebf6b9d38f7e94980664660b36cd8e60e4d8dd09c`。runner 在投递时按冻结清单校验制作源和提示。

```bash
python3 local/run_native58.py stage --materials /private/local_materials
# Spark 当前在线 8B 时
python3 local/run_native58.py producer --arm wrd58-8b-0 --profile yarn128
python3 local/run_native58.py producer --arm wrd58-8b-26 --profile yarn128
# Spark 当前在线 14B 时
python3 local/run_native58.py producer --arm wrd58-14b-0 --profile yarn128
python3 local/run_native58.py producer --arm wrd58-14b-26 --profile yarn128
```

每臂同源同提示、各自全新工作区，固定 1800 秒、单回复最多 32,768 token、最多 24 个模型 HTTP 请求。Agent 只接触本臂投递的输入。原生决定探索、执行、修订、停止或留待补证。保留 `outputs/skill/`、`outputs/trials/`、`outputs/versions/`、`outputs/evidence/decision.json` 中实际出现的文件与版本。逐个检查 `SKILL.md`、相对引用、按技能说明能否复现任务结果、修改前后有没有真实回归证据。只按实际产物或明确终止决策登记结果。

## C. 审核生成结果与制作成本

四个制作尝试结束后，审核实际生成文件和轨迹，逐项附原文件路径、版本 SHA、工具事件或测试记录。外层在终态后检查证据，不替模型生成资源、执行缺失制作步骤或补写修订链。

| 检查 | 证据与判定 |
|---|---|
| 会话理解与路线 | 保留用户纠正、确认与待确认事实，提炼可复用工作流；能指出路线与来源的关系。 |
| 资源构建 | 声明的脚本、模板和资料真实存在；输入输出、参数、相对引用和依赖一致。没有必要生成脚本的路线据实标 N/A。 |
| 制作内试跑 | 真实 read/exec 及反馈证明资源已运行；按任务适用性保留正常、边界、错误输入检查及实际输出。 |
| 反馈与修订 | 有失败时能够定位、修改并回归，版本与实际反馈前后相接；首次通过记 FIRST_PASS，不强造一次失败或修订。 |
| 封装与终态 | `SKILL.md`、资源目录、适用边界与用法对应；保留/修订/停止/待补证与当时证据一致。未通过的包不能仅凭进程成功变为合格。 |
| 自主完成与成本 | 由受测模型在同一原生循环完成；记录所有请求、工具操作、失败、回退、输入/输出 tokens、墙钟时间与预算删失。 |

按上述适用项全部通过并有可核验技能包的结果计 `PRODUCER_ACCEPTED`。合理停止或待补证的判断单独记为正确决策，不增加合格包数量。每臂报告包是否合格、各项证据、首次通过或修订情况，以及相对同尺寸基座的差值。所有制作尝试都计入分子，`每个制作验收合格技能的成本 = 同一臂全部制作尝试成本 / PRODUCER_ACCEPTED 包数`。分别报告 tokens、请求数和时间；有实测电费或价格再算货币值。分母为零时报告原始累计成本，单位成本记未定义。

这轮得到技能生成能力和制作成本证据。独立业务消费、无技能业务对照、消费盲评及原 `K_Q/K_R/K_G` 留在后续阶段，当前不执行。`freeze-skills` 与 `consume` 命令会在任何运行副作用之前拒绝。

## 同事完成后交回哪些文件

在授权私有交接位置提交一个 `wrd58-dev-return/`，按下列清单留存实物。Git 只归档去标识的汇总和经确认可分享的回执。配置密钥、真实会话、原始模型请求和未审查技能产物留在私有交接目录。

| 文件或目录 | 必须包含 |
|---|---|
| `spark_receipts/` | `serve_8b_128k.log`、`serve_14b_128k.log`、`smoke_8b_128k.json`、`smoke_14b_128k.json`，有异常时保留实际错误和失败回执 |
| `native_smokes/` | 四臂各一份 `smoke_result.json` 和实际 `outputs/result.json`，连同原生 session 事件、请求/回包及 `budget.json` |
| `dev_pilot/` | `stage_receipt.json`、四个制作工作区的 `producer_result.json`、终态或失败记录、实际产物/版本 SHA、原生证据、`budget.json` |
| `producer_review.json` | 四臂上述制作检查、实际证据路径及 SHA、`PRODUCER_ACCEPTED` 或其它终态、全部制作尝试成本；无消费评分 |
| `RUN_SUMMARY.md` | 记录操作者、Git commit、日期时间、设备架构、容器与基座/adapter SHA、每步 PASS/HOLD、实际部署时间和交付路径。按 8B-26↔8B-0、14B-26↔14B-0 报技能制作质量与成本的配对差值和实际失败 |
| `SHA256SUMS.txt` | 对回传文件逐件计算 SHA256，附相对路径 |

阶段 A 失败时交 A 的全部现有证据与具体错误，B 保持未开始。设备、传输、模型执行和技能包不合格各自记录。单组四臂用于首轮完整技能制作验证，独立来源扩展和教师制作对照继续采用同一生产任务口径。消费运行数为零。
