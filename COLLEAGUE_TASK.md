# 同事执行单：生成 skills 后一次回传

**2026-11-08当前执行修订：** 请先读 [接续单](20261108_NEXT_ACTIONS.md)。8B-26已按长输入终止失败报告暂停制作；其余臂按各自证据推进。下面原四臂说明保留来源与预算依据，本轮不要执行8B-26的producer命令，也不再等待四臂全部通过才开始首臂。

本轮让训练小模型担任 WRD 技能制作 Agent，从仓库内真实历史会话自主完成路线分析、资源构建、制作内试跑、反馈修订与技能封装。只做生成，消费派发数为 0。首轮为 **1 个真实来源 × 4 个模型条件，最多 4 份候选技能包**；四个版本属于同一来源。

## 1. 下载本分支和实际材料

```bash
git -c core.autocrlf=false clone --depth 1 --single-branch --branch codex/wrd58-colleague-handoff https://github.com/jiaotangbuding177/WRD_dataset.git wrd58-generation
cd wrd58-generation
```

已有本分支 checkout 时保存已有运行目录，再正常 fetch/pull；保留旧尝试，不用 reset/clean 覆盖结果。只需下载本分支当前普通文件，基座与 v2 adapter 复用 Spark 已验收的缓存。不要拿 main 上的旧 v1 adapter 替代。

`materials/` 已包含本轮全部制作输入：冻结 `DEV_MATERIALS.json`、26 条消息的完整原会话 `source.json` 和制作提示 `prompt.txt`，共 74,881 字节。原字节/SHA保持；历史消费字段仅作为原清单内容留档，当前不读取或投递消费文件。清单中的旧本机路径属于审计元数据，本轮投递不需要访问那些路径。[材料说明](materials/README.md)

在包根目录验收 SHA。Linux 用以下命令；Windows 用 `python` 替换 `python3` 后同样可运行包内 Python 脚本，以下多行校验也可按 PowerShell here-string 传入 Python。

```bash
python3 - <<'PY'
import hashlib
from pathlib import Path
for line in Path('SHA256SUMS').read_text(encoding='utf-8').splitlines():
    expected, name = line.split('  ', 1)
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name
print('bundle SHA256 PASS')
PY
```

## 2. 准备原生环境与服务回执

工具主机使用固定 **amd64 OpenClaw**，Spark **ARM64 只运行模型服务**。环境恢复、镜像摘要、导出/导入、容器到 Spark 连通均见 [OPENCLAW_RESTORE.md](OPENCLAW_RESTORE.md)。镜像二进制不在 Git 普通文件中；已有相同镜像直接复用，缺镜像时按该文档从持有者导出并导入。同事使用自己可连接 Spark 的主机，不要求本聊天所在主机登录 Spark。

先按 [VALIDATION.md A](VALIDATION.md#a-一次准备并验通两尺寸) 补齐或复用：

- 两尺寸的服务启动日志、长上下文验机 JSON，放 `local/spark_receipts/`。
- 四臂原生工具 smoke 的 PASS 回执，放 `local/runs/`。

当前 producer 入口检查以上四臂证据是否齐全。缺项时先 8B 验机、再 14B 验机，随后进行下面制作；已有同冻结配置通过记录直接复用。完整命令、预算和固定 adapter SHA 已集中在 VALIDATION.md，无需重跑此前完成的训练验收及144条短探针。

## 3. 投递并执行四次技能制作

在 **工具主机**的包根目录只投递一次：

```bash
python3 local/run_native58.py stage --materials materials
```

工作区已存在时先保留已有状态，勿重复 stage。每次 producer 保留真实终态，失败也回传，当前脚本拒绝覆盖已派发工作区。

在 **Spark** 包根目录启动8B服务，保持终端运行：

```bash
mkdir -p receipts
bash spark/serve_wrd58.sh 8b yarn128 2>&1 | tee receipts/serve_8b_128k.log
```

在 **工具主机**包根目录依次执行：

```bash
python3 local/run_native58.py producer --arm wrd58-8b-0 --profile yarn128
python3 local/run_native58.py producer --arm wrd58-8b-26 --profile yarn128
```

这两次均终态后，停止本次8B服务。在 **Spark** 同一包根目录切14B：

```bash
bash spark/serve_wrd58.sh 14b yarn128 2>&1 | tee receipts/serve_14b_128k.log
```

再在 **工具主机**执行：

```bash
python3 local/run_native58.py producer --arm wrd58-14b-0 --profile yarn128
python3 local/run_native58.py producer --arm wrd58-14b-26 --profile yarn128
```

四次均使用同一来源和原提示、干净独立工作区、相同原生环境，每臂1800秒、最多24次模型请求、单回复最多32768 tokens。让模型自己选择路线、执行工具、检查反馈并修订。保留原始推理响应、调用参数、工具反馈、真实失败和修订版本；不由操作者代写技能、补跑漏掉的模型步骤或捏造一次修订。首次通过据实登记。

当前26是contract课程终点，本轮结果归属于这些受测检查点。此次回传先供完整制作审核，过程课程其它检查点保留后续生成对照。

## 4. 找到生成的技能并回传

实际生成位置为：

```text
local/dev_pilot/producers/<arm>/workspace/outputs/skill/
  SKILL.md
  scripts/       # 模型按需生成
  templates/
  assets/
  references/
```

试跑、版本、终态证据在同一 `outputs/` 下的 `trials/`、`versions/`、`evidence/`。按模型实际输出保留；不补造空文件凑齐目录。**回传完整 producer 工作区，不只交 SKILL.md**，这样才能核查原会话→决策→操作→反馈→修订→技能包的真实链。

在包根目录填写 `RUN_SUMMARY.md`，记录操作者、`git rev-parse HEAD`、设备、镜像、四臂终态及异常；可按 `RETURN_TEMPLATE.json` 另存 `RETURN_FILLED.json`。随后运行：

```bash
python3 local/package_return58.py --out wrd58-generation-return.zip
```

把 **`wrd58-generation-return.zip` 和同名 `.sha256`** 一次交回。本包包含实际技能、完整制作证据、失败尝试、用量、验机回执与文件SHA清单；打包脚本不启动模型或修改技能。不要把全局凭据、SSH密钥或训练解密密钥放入回包。不要执行 `consume` 或 `freeze-skills`。

收到回包后，审核四臂的会话理解、路线选择、资源正确性、真实自测和修订、封装，以及每个制作验收合格技能的总成本。
