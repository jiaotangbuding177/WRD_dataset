# WRD58 v2 同事接手的验收与 DEV 小试

本文件从训练和离线选模完成处接续。验收 18/18、两组 checkpoint-0 基座一致性和 144 条短探针已经归档。只用 v2 的 0/26 检查点。[离线筛查提交](https://github.com/jiaotangbuding177/WRD_dataset/commit/4af0c4f1190a595d5b243026aaa68e7026ab0f17)

| 臂 | 角色 | adapter SHA256 |
|---|---|---|
| `wrd58-8b-0` | 8B 基座对照 | `27fb78e716391ef21bb3255fa00846e32e021bc2801f7d3391a73f62d84bbb47` |
| `wrd58-8b-26` | 8B 入围 | `2442a2e8f2dad2d5bdd88b0f4e054064548f28023246ea80473e46ddbc7dd786` |
| `wrd58-14b-0` | 14B 基座对照 | `a82c0cd548758be31f603d0f6b156f6ef57178363277bead42581e5df85a7512` |
| `wrd58-14b-26` | 14B 入围 | `81d2d09784f6d4239f9dd0fb1fa3b99930966e01d78d5c5f949c123f191d1792` |

两组的 26 都是 contract 阶段终点，这轮只比较这两个候选相对同尺寸基座的实际行为。Spark 使用冻结 Qwen3-8B `b968826d9c46dd6066d109eabc6255188de91218` 与 Qwen3-14B `40c069824f4251a91eefaf281ebe4c544efd3e18`。Spark 每次载入一个尺寸，在同一服务同时暴露该尺寸的两臂。

## A. 一次准备并验通两尺寸

1. 先按 [OpenClaw 恢复](OPENCLAW_RESTORE.md) 在与 Spark 能建立受控连接的 **x86_64** 主机导入固定 `linux/amd64` 镜像。该主机持有工作区与受控 DEV 材料。ARM64 Spark 负责 vLLM。确认 x86 主机上的 Docker 容器可以通过本地 relay 访问模型接口。Windows 到 Spark 的人工逐包交接只用于合成诊断，耗时单列。
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

   原生烟测每臂 300 秒、最多 8 个模型 HTTP 请求、单次输出最多 1,024 tokens。`local/runs/smoke-yarn128-<arm>-01/smoke_result.json` 须全项 `PASS`。它检查原生完整读 `SKILL.md`、真实 `exec`、正确文件 `outputs/result.json`（`sum=42` 与 `proof=native_exec`）、下一模型请求含工具结果、完整原生工具配置、结构化调用、thinking、实际用量和请求身份。失败时保留原尝试并写原因。确认修复后以新 `--attempt` 单次执行，保留旧耗时与用量。

## B. 先做一组四臂制作

正式 DEV 共冻结四个来源。当前只有 EDU 文本组 `conv_497a2363eddb` 可投递，范围限定对外短文流程，另有两道虚构事实简报作独立消费。`LEGAL` 组缺原协议和承诺函，`BIZ` 组缺原招标文件和投标成品，`OFFICE` 组缺原 PNG 序列和大纲。三组记 `HOLD_ORIGINAL_MATERIALS`。一组通过后只报告本组证据。补齐缺件必须核来源与 SHA，再按同一四臂协议扩展，保持原 226 来源与正式 TEST 隔离。

从授权私有路径取得原冻结 `local_materials/`。内有 `DEV_MATERIALS.json`、制作源与提示、独立消费输入和评审规则。Git 包只提供启动器、配置与合成诊断资源。实际业务源件与评审材料单独交接。当前 EDU 原始源为 62,997 字节，SHA256 为 `adf496e34aa109450dcf4c1ebf6b9d38f7e94980664660b36cd8e60e4d8dd09c`。runner 会在投递时按冻结清单逐文件校验。

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

## C. 在固定 Actor 上做消费与评分

四个制作尝试都有终态后，用 `freeze-skills` 登记实际技能树和 SHA。先按 B 中的验收要求人工复核四个候选包的范围与资源引用。消费阶段固定用 Spark 现有 `wrd58-8b-0` 作 Actor，所有消费槽均使用相同的模型、工具环境和预算，在独立新会话运行。这里测量的是在此固定 Actor 下的技能可用性。

```bash
python3 local/run_native58.py freeze-skills
# Spark 切回 8B yarn128，且保持服务在线
for case_id in partner_notice_confirmed_and_pending public_notice_sparse_brief; do
  for arm in no-skill wrd58-8b-0 wrd58-8b-26 wrd58-14b-0 wrd58-14b-26; do
    python3 local/run_native58.py consume --arm "$arm" --case "$case_id"
  done
done
```

每道题含四份制作技能与一个共享无技能对照，最多 10 个模型运行槽。两道消费题同属一个开发来源组，统计独立组数时计 1。每道题只复制自己的 `input/` 与所分配技能，盲评标准 `evaluator_only.json` 留在评分端。无可运行技能的臂保留原槽并登记消费未启动与理由。结果进入 `local/dev_pilot/consumers/<case>/<arm>/`。

逐个记录技能的原生发现和实际读取、工具与资源使用、`outputs/answer.md` 可读性、硬检查、盲评 Q 与实际用量。Q 按正确性 30、完整性 20、适配 20、专业可用 20、呈现 10 加权，单项按冻结规则计 0/0.5/1。该材料目前标记 `DEV_CALIBRATION_PENDING`，先记录 Q 和硬验收事实，资格阈值校准前把正式资格标记 `pending`。`K_Q` 在包可靠、独立消费通过及 Q 达冻结线后成立。`K_R` 需要原生真实复用、交付达标、账齐，并且同版本所有业务尝试的 token 合计和调用合计都低于同题无技能对照。`K_G` 是两者交集，每个预登记来源组至多计一个。全部尝试、异常和回退的花费保留，缺用量为 `unknown`。账缺或基线失败的槽单列，`K_G=0` 时保留费用和未定义的单位成本。固定 Actor 接线需通过其端点验收后再执行消费。

## 同事完成后交回哪些文件

在授权私有交接位置提交一个 `wrd58-dev-return/`，按下列清单留存实物。Git 只归档去标识的汇总和经确认可分享的回执。配置密钥、真实会话、原始模型请求和未审查技能产物留在私有交接目录。

| 文件或目录 | 必须包含 |
|---|---|
| `spark_receipts/` | `serve_8b_128k.log`、`serve_14b_128k.log`、`smoke_8b_128k.json`、`smoke_14b_128k.json`，有异常时保留实际错误和失败回执 |
| `native_smokes/` | 四臂各一份 `smoke_result.json` 和实际 `outputs/result.json`，连同原生 session 事件、请求/回包及 `budget.json` |
| `dev_pilot/` | `stage_receipt.json`、四个制作工作区的 `producer_result.json`、终态或失败记录、实际产物/版本 SHA、原生证据、`budget.json` |
| `consumption/` | Actor 冻结信息、10 个已规划槽的终态（含未派发）、最终文件、证据/盲评及各次完整用量，评分缺项与错误理由 |
| `RUN_SUMMARY.md` | 记录操作者、Git commit、日期时间、设备架构、容器与基座/adapter SHA、每步 PASS/HOLD、实际部署时间和交付路径。按 8B-26↔8B-0、14B-26↔14B-0 报配对差值和实际发生的失败 |
| `SHA256SUMS.txt` | 对回传文件逐件计算 SHA256，附相对路径 |

阶段 A 失败时交 A 的全部现有证据与具体错误，B/C 保持未开始。设备、传输、模型执行和业务不合格各自有独立记录。单组小试回答原生接续与初步业务差异，正式替代能力留待后续冻结的独立来源与教师对照。
