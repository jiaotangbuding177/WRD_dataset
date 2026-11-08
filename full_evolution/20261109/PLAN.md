# 全量演化集恢复与真实skills交付实验

日期：2026-11-09。目标是训练后的模型在原生OpenClaw内自主理解会话、筛选路线、制作资源、真实试跑、必要修订并交付skills。不是只验证接口或格式，也不是让人逐工具下指令。本次交付材料与执行准备，未启动推理、训练或业务实验。

## 1. 本次交付的实际材料

完整保存1107个来源、12类任务，不再只交1个文本案例。每个来源同时具备：

- 默认 `source.json`：与原WRD实际输入母本相同的完整清洗会话，合计22070条消息。
- 原审计副本：36991条消息，含原导出重复别名；单独保存，不将重复当新经验或默认上下文。
- 原生业务重放视图：5567轮用户输入、后续轮次和原资源可用时点。
- 资源实体：3321个按内容SHA去重的对象，921629345字节；8231条投递关联，含1316次后轮投递。
- `resource_index.json`：原路径、原轮次、当前可读挂载路径、SHA及原始/重建来源。历史正文不改写。
- 原母本、881演化/226评测合同、旧source_bindings、现材料映射、6来源已验证修订、训练隔离注册和构建/核验脚本。

“全量”指完整1107来源及现有材料实物都入包。物理核验为所有**已声明文件**存在且SHA一致；原会话提及但从未恢复的附件、材料重建身份和语义边界另外记录，不将其伪称认证原件。原226继续不反哺学生SFT；本包不会改变已经训练的1260目标、loss、课程或权重。

材料采用普通Git二进制分卷，每卷不超过16MiB，含实际内容，不是LFS空指针、外部路径或仅候选清单。不加AES加密，无需另找密钥。两个实体层为resources与records；`DELIVERY.json`钉每层清单，清单再钉每卷及整体archive SHA，恢复后全成员再验。

## 2. 历史pipeline究竟怎么收到材料

已核的历史主链为：

`pipeline.json → source_bindings.json → v11有效轨迹母本/完整conversation → screen → make → prepare → 同型任务双臂试用 → review`。

screen/make实际拿完整会话，make加来源资源及已有制作反馈；prepare读取全用户需求目录，后续真实试用和review完成取舍。历史121条生成路线中29 retained，不能将121个目录都当成功skills。

发现并纠正投递口径：旧bindings有8058资源关联，却只有122项通过旧 `eligible_real_input` 过滤，因此大量重建件没有被那条旧路径投递。本次不照搬这个原件认证过滤；复用后续原生case映射与6来源修订，保留synthetic、provenance和user_index，再投递现有实际文件。旧过滤规则和失败证据一并保留在 `HISTORICAL_DELIVERY.md`，不改写历史成绩。

maker是回顾性学习任务，可以读取该会话各历史轮已提供的材料；原生业务重放仍需按user_index逐轮投递。maker文件改挂到按轮隔离的 `inputs/source_resources/`，索引明确原路径映射，避免同名历史版本覆盖；这不是伪造原始输入，也不是把后轮成品冒充首轮答案。

## 3. 模型与执行器分别负责什么

模型接收一次完整沉淀目标、完整会话和资源索引，自行选择读、写、执行、检查、修订和结束。实际输出为Git工作区 `outputs/skill/` 及包外 `outputs/trials/versions/evidence/`。

固定OpenClaw提供原生53工具、skills发现/读取和会话循环。外层只准备输入、分发独立任务、管理预算和留存证据，不实现替代Agent循环，不自动修工具参数，不代写SKILL，不根据进程退出0判成功。

执行入口明确这是用户自有普通Git仓库的skill源码工作，使用native已有的repository-owned例外。prepare真实初始化仓库并提交初始输入，固定consumer将整个真实workspace挂到容器/workspace，.git/HEAD/objects与实际挂载声明已有CPU证据；尚未把CPU证明说成容器内或模型已成功执行。

## 4. 本轮固定哪些真实来源

从完整档案中冻结12个新独立来源，OFFICE/LEGAL/EDU/HR/BIZ/DATA各2个。按固定source哈希排序选，排除旧24角色、实际58训练直接来源与已记录identity闭包；0模型成绩参与选题。`EFFECT_FREEZE12.json`保留选择规则、排除原因、source SHA与实际训练边界证据。

这些不是12个必然应产包的正例。运行前独立阅读完整历史后，冻结如下分层；该评审不是旧teacher逐源成功标签，且**不挂载给模型**：

| 顺序 | 来源 | 类型 | 本轮评价 |
|---:|---|---|---|
| 1 | conv_1695d8fd2aca | OFFICE | 制作：参考图片/HTML构建方法；缺失原图不能补造成原件 |
| 2 | conv_315b16c7b8ce | LEGAL | 制作：结构化信息收集与分析路线，不伪造法律事实 |
| 3 | conv_25f59d660ad2 | EDU | 制作：教学动画构建与验证 |
| 4 | conv_2bd200526fe5 | HR | 制作：知识库整理与结构化资源处理 |
| 5 | conv_f9f4cc0a8b38 | BIZ | 制作：基于已知资料的分析工作流，不新增企业事实 |
| 6 | conv_fbc466c9dfb1 | DATA | 制作：账表处理/核对；自测需完整新fixture，不能虚报原股权表已恢复 |
| 7 | conv_276e97b595fc | OFFICE | A筛选：原历史只有模糊logo需求与追问，应停止/说明所需输入 |
| 8 | conv_63a92ea9ec3c | LEGAL | 制作：材料审阅/修订及公开口径边界 |
| 9 | conv_cc021b31849c | EDU | 制作：依据作业资料进行分析与反馈 |
| 10 | conv_e17409b249a6 | HR | 制作：文档读取排错/结构化分析；不伪造原简历事实 |
| 11 | conv_34843d227bc0 | BIZ | A筛选：没有企业资料，历史仅追问，应停止/列缺口 |
| 12 | conv_77e95f792ca5 | DATA | 制作：报告到展示的提取/制作/修订；无原招股书不编原财务数据 |

具体已知缺口、可执行测试范围与原业务重放状态见恢复后 `evaluator_only/SEMANTIC_REVIEW12.json`。10例可以评价制作，需以完整、受控的新输入真实试跑；2例评价正确拒绝，不能把正确STOP当生成失败。**撤销此前统一“10/12产包”的部署目标**，改为A筛选12例、制作10例分别报告。

1107全部实物可通过generic入口使用；其他已见或未独立冻结来源需显式 `--allow-seen-diagnostic`，输出标SEEN/非盲诊断。档案完整不等于1107全部都是未见测试或SFT数据，不自动启动全量生成。

## 5. 同题四臂与共同预算

主比较14B-241对14B-0；次比较8B-241对8B-0，共12×4=48原生会话。基座revision与v2 adapter实际SHA由启动脚本核验；不能使用main旧v1错误训练方向权重。26退出本轮效果实验。

固定OpenClaw镜像ID `sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2`、工具、依赖、模型精度与服务采样。所有组全新独立Git工作区，不挂他臂skills、评审答案、全局材料档案或已学习库。仅挂本source及其资源；评估侧文件留在宿主。

Spark ARM64只推理，工具宿主运行既有amd64固定OpenClaw；复用同事已恢复的镜像、模型缓存和v2权重，无需重装。镜像二进制和基座不在本材料分卷里，固定身份及导出/导入办法见原分支 `OPENCLAW_RESTORE.md`。

- thinking ON；temperature .6、top_p .95、top_k20、min_p0。引擎seed58，native没有转发逐请求seed，故不声称逐请求随机数严格配对。
- 同一YaRN128K服务条件；工具schema本身约31K，不假称真实制作都在32K SFT窗口内。
- 每任务24次模型HTTP、单回复8192、累计completion32768、墙钟3600秒，先触顶即止；含reasoning、原生finalization、原生重试和同端点子会话。
- 保留原HTTP body，按下一次完整8192上限保守预留；剩余额度不足接纳请求时停止，不偷偷改写max_tokens。未知usage保留预留，与实测分账。
- 所有失败、预算终止、部分响应和费用保留。18759中继单owner，在派发标记前独占；编号attempt禁止覆盖或盲重试。
- 同源0/241顺序事前交替；每尺寸分组运行降低加载次数，冷启动/加载/转移单列。

48次全部触顶最多48 Spark任务小时、1572864 completion tokens、1152模型HTTP请求；这不是实际用时预测或执行授权。先做首3来源×4臂12次真实制作，均属于同一个实验。

## 6. 直接给同事的完整执行顺序

### 工具宿主：下载和恢复，纯CPU

```bash
git -c core.autocrlf=false clone --depth 1 --single-branch --branch codex/wrd58-colleague-handoff https://github.com/jiaotangbuding177/WRD_dataset.git wrd58-generation-full
cd wrd58-generation-full/full_evolution/20261109
python3 tooling/restore_corpus58.py --delivery DELIVERY.json --out corpus
python3 tooling/restore_corpus58.py --verify-only --out corpus
cd execution
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase first3 --size 8b --runs runs --dry-run
```

Windows将python3换python。上述命令不启动模型。第一次clone取得实际分卷，不需要AES密钥；已clone时正常更新并保全旧运行目录，不reset/clean。

### Spark：使用已有缓存启动8B服务

Spark只需要本次 `execution/spark/serve_wrd58.sh`，不必复制完整1.36GB会话材料到Spark。将该目录带到Spark，同事按机器已有路径设置 `WRD_WORKSPACE_ROOT`（包含out58_8b_v2/out58_14b_v2）和 `WRD_HF_ROOT`（包含hub/），或由已有wrd_build挂载自动发现；`WRD_VLLM_IMAGE`使用上一轮成功服务的同一实际本地镜像。

```bash
mkdir -p receipts
bash spark/serve_wrd58.sh 8b yarn128 0,241 2>&1 | tee receipts/serve_8b_128k.log
```

保留服务终端；启动命令显式含VLLM_ALLOW_LONG_MAX_MODEL_LEN=1。确认旧WRD服务无未结束请求后再由同事停止旧服务并切换，脚本不擅自杀在途服务。将实际启动日志原样复制到工具宿主execution/receipts/。

### 工具宿主：一次跑当前尺寸首3来源

保持同事已经建立的宿主到Spark模型连通，不要求本聊天电脑SSH Spark。

```bash
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase first3 --size 8b --startup-log receipts/serve_8b_128k.log --runs runs
```

该6任务全部终态后保存8B日志，在Spark切换14B，带回启动日志：

```bash
# Spark
bash spark/serve_wrd58.sh 14b yarn128 0,241 2>&1 | tee receipts/serve_14b_128k.log
```

```bash
# 工具宿主
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase first3 --size 14b --startup-log receipts/serve_14b_128k.log --runs runs
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase review-template --runs runs --out prefix_review.json
python3 local/package_corpus_return58.py --runs runs --selection ../corpus/EFFECT_FREEZE12.json --receipts receipts --out wrd58-full-maker-first3.zip
```

带回 `wrd58-full-maker-first3.zip`、`.zip.sha256`、`prefix_review.json`。**先看真实技能与内容，不再跑接口烟测。** 评审只在任务结束后进行，不能补写技能或为某个模型改题。

### 首批内容审核后，按固定条件继续同实验余9来源

审核12个真实结果，填写模板中review_status=CONTENT_REVIEWED、qualified、qualification_count、review_evidence，绑定实际producer_result SHA；技术失败不能假填内容不合格。首3都属于制作分层，两个241都0合格则入口停止余9，不换题/加预算/挑checkpoint追正例。首批报告为3来源工程结果，不冒称完整12样本结论。

有有效审核且未触止损时，先趁14B已加载执行其余9来源，再切8B：

```bash
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase remaining --size 14b --startup-log receipts/serve_14b_128k.log --runs runs --review prefix_review.json
# Spark切回8B、更新其真实启动日志后：
python3 local/run_effect58.py --corpus ../corpus --selection ../corpus/EFFECT_FREEZE12.json --phase remaining --size 8b --startup-log receipts/serve_8b_128k.log --runs runs --review prefix_review.json
python3 local/package_corpus_return58.py --runs runs --selection ../corpus/EFFECT_FREEZE12.json --receipts receipts --out wrd58-full-maker-return.zip
```

带回最终ZIP、同名.zip.sha256和已填prefix_review.json；不要只交摘要或SKILL.md，原生推理/工具/错误/版本/成本全部在包里。

## 7. 如何评价真正的技能与训练收益

1. **A决策：12例。** 能否识别有根据的制作路线，以及在2个证据不足案例正确STOP/说明输入需求。正确拒绝不算技能产包，不算制作失败。
2. **合格制作：10例。** 实际SKILL及资源存在；范围/事实有来源；公开用法可运行；真实适用试跑通过；有修订则旧版→反馈→变更→复跑可追溯；最终声明与实物一致。单独报告每来源是否≥1合格包及去重技能总数。
3. **质量Q独立报告。** 来源忠实、工作流可执行、资源正确自足、验证修订可靠、封装易用，各0—4分换算100。缺产物N/A并报覆盖，Q差值只用双方共同可评分来源，不用成功×质量归零。
4. **完整链证据。** 制作内试跑与资源功能复验在本轮；若没有原WRD真实有/无技能效能比较，C效能和完整A—D记NOT_EVALUATED，不把资源自测冒充业务减负。独立业务消费仍延期。
5. **训练因果对照。** 同尺寸241对0，唯一模型变化为adapter，材料/任务/环境/预算共同；先看逐来源胜平负，再看合格率、Q和成本。14B为主，8B描述性次比较。制作二元检验采用有效完整正例配对的exact McNemar，公开实际n（最多10），不将48会话或10×4当独立来源。

工程目标改为：241在10个制作案例至少8个合格、2个不足证据案例不虚构产物，且可评分Q均值≥80。目标不是已获成绩或通过保证。只要基座同样表现，就不能把可用性直接称训练增益；241更差需如实记负迁移。

## 8. 每个合格技能的全部成本

每臂全部12任务的推理占用秒、input/output/reasoning、工具、外部API、人工作业及失败开销留全账。正确STOP成本也计入生产系统成本，避免只算胜出任务。

`单位合格技能制作成本 = 本臂所有尝试总成本 / 去重合格技能数`。

另报每成功来源成本防拆包刷数。0合格时不声称节省。首先用实测机器秒/包和tokens/包，未知usage/预留不冒充实测；API USD0占位不当免费。将数据准备+实际训练成本按未来累计合格包数摊销，并与本次研究验收费用分列。

若要声称替代原大模型并节省多少费用，还要同输入/环境/预算的教师参考；历史29保留路线不是逐source独立金标，也不能直接拿历史异条件费用作当前节省率。本轮先回答实际交付及0→241训练净效应。

## 9. 当前已经验证与尚未运行

已做：全量实际文件复制和哈希、6源修订、原始/清洗/重放视图保全、训练边界复核、12来源静态语义审核；新执行接口CPU检查、端口独占、账本/原SSE透传、真实Git与原生挂载声明，以及12×4=48个真实材料prepare/verify。

CPU临时工作区和假上游不进入生产语料、不算技能产物；固定native runtime七文件逐SHA不变。最终数据还将从Git远端冷下载分卷、在独立目录恢复并逐成员核验，回执随交付给出。

未做：启动Spark推理、新OpenClaw业务会话、全量生成、微调/重训、独立消费。不会把“包上传/CPU过”说成模型已经生成了技能。下一次真实工作直接执行首3的实际制作与产物审核。
