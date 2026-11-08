# 完整训练终点241：一轮小预算对照与真实技能制作

本轮主角是 **8B-241与14B-241**。241此前已参加12题短探针，8B为8/12、14B为6/12；26分别8/12、9/12。这些短题偏向契约、字段和规则，不能据此把26当作唯一原生制作候选，或跳过241的长输入与完整制作验证。当前比较0/26/241，并让两个241实际制作skills。26的已知长输入失败保留，消费继续为0，不重训。

## 本轮一次拿到什么

| 部分 | 运行 | 输出上限 | 墙钟上限 | 直接回答 |
|---|---|---:|---:|---|
| 收尾对照 | 每尺寸0/26/241 × nominal24K/66K，共最多12个API请求 | 每请求128，合计1536 tokens | 每尺寸600秒，合计20分钟 | 不收尾集中在26、241、训练后两者，还是共同长输入条件 |
| 实际制作 | 8B-241与14B-241各1次原生OpenClaw制作 | 每次最多6模型请求、每回复2048，合计24576 tokens | 每次900秒，合计30分钟 | 完整训练产物能否真正操作环境、试跑修订并生成技能包 |

本轮最多 **24个模型HTTP请求、26112输出tokens、50分钟任务预算**，不含模型加载与文件传输。输入tokens单独按实际用量计，不把预填充当免费。请求失败、重试、超时和异常全部入账；原生自然重试也受同一6请求上限。没有额外241玩具技能消费烟测，也不再跑32768输出的填充请求。

收尾矩阵给OFF模式固定seed与同一采样参数，两个长度都用同一yarn128服务；真实制作沿原生thinking ON及原生产采样，输入仍为仓库完整原会话与原提示，只追加两尺寸相同的可见预算说明。这两部分各自回答不同问题，不能拿简单OK通过冒充技能制作通过。

## 两台机器的任务

同事使用自己能连接Spark的工具主机。Spark只推理；固定amd64 OpenClaw在工具主机操作文件与工具。镜像恢复见OPENCLAW_RESTORE，原制作材料已在materials，不需要重新提供会话。

### 先更新本分支

保留已有产物和日志，再更新 `codex/wrd58-colleague-handoff`。新克隆可用：

```bash
git -c core.autocrlf=false clone --depth 1 --single-branch --branch codex/wrd58-colleague-handoff https://github.com/jiaotangbuding177/WRD_dataset.git wrd58-generation
cd wrd58-generation
```

按SHA256SUMS核验当前文件。只用v2的`out58_<size>_v2`，Spark已有基座缓存与权重直接复用。241 adapter SHA如下：

| 模型 | adapter_model.safetensors SHA256 |
|---|---|
| 8B-241 | `dc63b9d4646a05bebc2394192ea56ee7bd3009211576a6f0c659c683786b7ccb` |
| 14B-241 | `a8e9ba53a6be6d37cc6d86a988225a3da7539d9d4e396666a9ccbeaae62d2e25` |

新服务脚本默认同时暴露0/26/241，每个alias都校验实际权重SHA；同一尺寸仍只加载一个基座，用同一固定镜像、YaRN、工具解析与采样配置。

### Spark：8B先完成对照

先保留旧日志。确认当前WRD58推理服务没有未结束请求后，停止该服务以切换到含241的配置；不需要重启训练环境。

```bash
mkdir -p receipts/final241
bash spark/serve_wrd58.sh 8b yarn128 0,26,241 2>&1 | tee receipts/final241/serve_8b_128k.log
```

服务终端保持运行，另一个Spark终端在同一包根目录执行：

```bash
python3 spark/compare_checkpoints58.py 8b --startup-log receipts/final241/serve_8b_128k.log --out-dir receipts/final241/compare_8b
```

顺序优先241与基座，26最后作为阶段参照：short241、short0、long241、long0、short26、long26。每请求最多128输出、至多180秒；每尺寸总600秒，预算状态在同一输出目录持久保存。超时或中断不自动重试，超过组预算的未派发项据实标SKIP；不要通过换目录反复追加预算。真实token数量由回包核实，nominal24K不能仅凭字符数当作实测24K。

### 工具主机：直接让8B-241生成skills

把Spark本轮真实启动日志原样放到工具主机包内 `local/spark_receipts/serve_8b_128k.log`，先将旧同名日志保留到备份位置；把整个`compare_8b/`复制到 `local/diagnostic_evidence/final241/compare_8b/`，启动日志也在该诊断目录留一份。无需把每次请求人工往返，本阶段继续使用同事已建立的模型连接。

```bash
python3 local/run_native58.py stage --materials materials
python3 local/run_native58.py producer --arm wrd58-8b-241 --profile yarn128 --budget mini
```

stage可从旧四臂投递安全扩充到六臂，先验证旧源/提示/请求哈希，备份旧stage回执后仅新增241；不会覆盖已产生的0/26轨迹或技能。mini制作单独放在`local/dev_pilot/producers_mini/`，保留原完整制作目标和输入，初始提示明确900秒、6请求、每回复2048的预算。

mini是明确声明的有界原生试验，启动前核固定镜像、包装文件、实际live alias、基座/adapter SHA、服务上下文和共同配置。目标241的原生协议能力在这次真实制作中直接接受检验，不要求先过一轮玩具技能烟测，也不把尚未发生的工具执行写成PASS。若收尾短题出现length，仍可做这一次有界制作，从真实任务检查结果；不擅自增加预算或把截断伪装正常结束。

### Spark与工具主机：14B按同样步骤一次完成

8B对照和制作都有终态后，保存日志并切换同一固定服务镜像的14B，避免来回反复加载模型：

```bash
# Spark服务终端
bash spark/serve_wrd58.sh 14b yarn128 0,26,241 2>&1 | tee receipts/final241/serve_14b_128k.log
```

```bash
# Spark另一终端
python3 spark/compare_checkpoints58.py 14b --startup-log receipts/final241/serve_14b_128k.log --out-dir receipts/final241/compare_14b
```

将14B启动日志和整个比较目录原样带到工具主机对应位置，再执行：

```bash
# 工具主机，无需重复stage
python3 local/run_native58.py producer --arm wrd58-14b-241 --profile yarn128 --budget mini
```

0和26只需跑本轮有界收尾对照；8B-26的producer HOLD继续保持。不要将26的制作暂停扩大为禁止对它做这次128输出的对照。

## 怎样解读回包

### 收尾对照

每条都分开记录实际输入/输出tokens、HTTP与模型身份、`finish_reason`、`stop_reason`、是否自然停止、答案是否严格OK、完整响应和请求SHA。`length`记输出预算耗尽；HTTP/时间预算失败不当作自然收尾失败。自然停止但答错OK，记指令执行问题。

| 同一尺寸同一条件下的结果 | 本轮判断 |
|---|---|
| 0与241正常，26不正常 | 异常集中在26，不能用26代表完整训练产物 |
| 0与26正常，241不正常 | 完整过程训练终点出现退化，优先审过程课程与该权重 |
| 0正常，26与241都不正常 | 有训练后共同退化迹象，再按24K/66K分层定位 |
| 24K正常，66K异常 | 异常主要出现在当前长输入/扩窗条件，不混称所有输入都坏 |
| 0、26、241都异常 | 先核共同服务、采样与任务条件，不能单独归因adapter训练 |
| 达时间/总预算或无完整回包 | 对应项记TIMEOUT/SKIP/UNKNOWN，保留成本，不猜测停止行为 |

以上是对受测条件的诊断。EOS、采样、模板、YaRN和训练监督的根因，结合实际配置与原始输出审核；不靠改stop字符串、截`</think>`或提高重复惩罚来掩盖原结果。本轮不启动重训。

### 真正生成skills

每个241单独给出以下事实，而不只看进程是否成功：

1. 实际读到原会话、保留用户纠正、确定/待确定事实和路线边界。
2. 由受测模型真实写出`outputs/skill/SKILL.md`及按需资源，引用和用法对应。
3. 真实运行制作内试验，记录输入、期望、实际结果及工具反馈。
4. 若发生修订，前后版本能与失败及回归相接；首次通过如实记FIRST_PASS。
5. 最终包内容正确性与完整性、实际终态、全部制作成本分别审核。

得到合格包且正常收尾，说明完整训练模型在本来源上完成了自主技能制作；有包但内容/自测有缺陷，报告具体缺陷；包已成但持续生成，单独报告生成能力与收尾缺陷；预算用尽仍无合格包，报告实际完成步骤和预算，不伪造成功或直接断言所有标准预算任务都不行。资源数量多不直接加分。这里验技能制作，不派业务Actor消费。

## 一次回传

把本轮Spark `receipts/final241/` 全部复制到工具主机 `local/diagnostic_evidence/final241/`。保留此前8B-26两次长测原件及实际脚本。填写RUN_SUMMARY.md，随后执行：

```bash
python3 local/package_return58.py --out wrd58-final241-return.zip
```

回传 **`wrd58-final241-return.zip`及同名`.sha256`**。包中应有两个241的mini工作区、实际skill、试跑/版本/终态、原始推理与工具轨迹、全部用量、12项对照的已执行/未执行状态和权重/服务身份。回包清单的`mini_arms`是本轮两个主要制作结果；旧`arms/pending_arms`仍列standard历史状态，不要求为清空该字段额外派发标准制作。收到后即可回答“26是否特殊、241是否也退化、完整训练产物实际生成了什么skills”，不再只交短探针分数。
