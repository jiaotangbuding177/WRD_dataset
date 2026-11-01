# WRD最终训练方案58：14B主线、8B对照

设计版本5.0.58；变更ALG-20261102-01；接口workflow-pipeline-v1；日期2026-11-02。前版57全部作为历史保留。本轮进行CPU数据审计、精确mask增强、课程/选模修正和Git交付，不加载学生权重、不推理、不训练、不派新教师会话。

## 训练目标与预期产物

训练一个**WRD领域策略V1**：输入完整会话路径、沉淀目标、允许材料和预算，模型在固定原生OpenClaw中自行读取、选择工具、制作程序/模板/资料、观察反馈、局部修订、验证和交付skill目录。模型每次输出标准思考/工具调用或最终回复；OpenClaw负责真实工具执行与会话循环。输出目录为`outputs/skill/`，V0/V1及试跑证据在包外保存，不要求用户逐步提供阶段标签。

预期最强收益是B资源构建、接口遵循与局部修复；A的需求契约/路线规范和D的封装也有直接训练支持。C的独立质量取舍与完整跨任务长流程，以来源隔离的真实闭环结果衡量。这里预估的是能力结构，未给未经训练测量的TSR百分比；详见`QUALITY_FORECAST58.md`和原始论文核查。

## 实际训练材料

新58保持**1260个唯一目标、相同曝光次序和来源**，增加650个可信协议F监督后共**295478个正监督tokens**。

| 池 | 唯一目标 | 正监督tokens |
|---|---:|---:|
| 来源契约 | 401 | 67758 |
| 旧真实过程 | 178 | 143916 |
| 上轮恢复过程 | 21 | 3481 |
| 新原生链（同33窗口，协议增强） | 33 | 22961 |
| 明确标注的辅助课程 | 627 | 57362 |
| 合计 | 1260 | 295478 |

真实过程仍为232目标、59来源ID/46身份组件；同一制作链的33窗口不算33独立任务。真实过程阶段A7/B166/C21/D12/历史R26；另401契约属于A，627辅助属于A48/B170/C232/D177，整体A456/B336/C253/D189/历史R26。全TRAIN含契约为287来源ID/261身份组件。原226、H12/static、reserved和已冻结dev/test的来源及资源血缘继续隔离，旧44目标不回流。

R组件仍78938正tokens，必须拆来源：原teacher R共57200正/77目标/12来源ID/9组件，其余为新作者真实状态理由与明确合成理由。原provider R与同turn记录动作配对为38目标/5来源ID/3组件。新原生链provider原思考39679字符全文、33响应/32工具反馈、失败和版本原件均在前版57中保留，本次不重写或删去；新增F不是新思考或新独立经验。

两种profile互斥，正目标完全相同：默认budget_projection为10631405序列tokens、934条≤16K/326条16—32K；full_native53旧参照名为21207839、532短/728长，0超32K。新33在两profile中均为相同past-only状态，原完整33请求另留审计，不能把profile名字当全部完整历史。输入/未授信正文零loss仍有前向成本。

## 本次三项实际修正

**动作协议补强。** 旧库已有工具名和结构监督；本次针对新增完整链补足31个schema有效且实际native ACK调用的tool_call边界、工具名、参数键/结构、think边界及结束符，共650个F tokens，权重0.25。只选完整落在审定字符范围内的token，不碰argument value、原R/可见正文、随机call ID或role header。API5曾用错误edit参数、原A为0，整条mask维持；API33最终说明也维持。旧22311个R/A/D正token、全部input_ids/messages/tools/target及权重逐字不变。新增31个EOS是正确的工具回合结束，不是给失败技能追加成功终态。

**逐优化步骤辅助系数上限。** 在每个process累积批，从实际基础weights计算真实系数mass M_real和辅助mass M_aux，令`alpha=min(1,0.25*M_real/M_aux)`；无辅助时alpha=1。只对synthetic额外乘一次alpha，使该步辅助系数mass占比≤20%。bin保留原loss_weights，COURSE58记录alpha和effective mass，trainer不得误以为bin已经缩放。上限针对系数mass，不声称限制CE值、梯度或Adam参数变化。此修正避免仅凭全局低权重解释单步训练影响。

实际两profile四features→课程复验已通过：基础mass85003.30，课程effective总84227.1375，aux2091.9375，占全局2.48369%/过程4.57310%；92步需要额外缩放，全部215过程步≤20%。**过程阶段**按步归一化的辅助系数占比从旧57的15.53%变为9.39425%，它同样不是梯度占比。后置`objective_adapter58.py`提供base features到effective weights/统一分母的可执行CPU接口和防重复缩放检查；trainer应调用该合同，不能只读取base bin忽略课程alpha。实际模型训练仍为0。

**中途选模。** 单pass最多241更新不变；候选checkpoint为base0、26、80、134、188、241。先用独立dev诊断筛选，再对候选做原生闭环比较，不只看训练loss，也不自动选最后一步。base0是未SFT对照，不是新增更新。test始终不参与选模或设门槛。

## SFT精确配置

- 主模型`Qwen/Qwen3-14B@40c069824f4251a91eefaf281ebe4c544efd3e18`；对照`Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218`。
- BF16底座冻结，embedding/lm_head冻结但保留通过冻结层的梯度；LoRA r32、alpha64、dropout0.05，覆盖q/k/v/o及gate/up/down投影。理论LoRA参数14B为128450560、8B为87293952，不把它写成实测显存。
- AdamW lr5e-5、betas(0.9,0.999)、eps1e-8、weight_decay0.01、grad_norm1；constant_with_warmup，warmup3全局更新，跨阶段不重置。
- microbatch1、gradient checkpointing/non-reentrant、use_cache=false；最大训练序列32768，不静默截断、不重模板、不跨例packing。
- 401契约acc16→26更新；859过程（232真实＋627辅助）acc4→215更新；尾批1/3真实flush，每ID一次，不复制填尾，同adapter/optimizer贯穿。
- 单次累积更新的loss为`sum(CE_i * base_weight_i * step_scale_i) / N`。step_scale仅synthetic用本步alpha，其余1；N是该累积批全部非ignore shifted target数，**不按权重和归一化，不再除accumulation**。先按完整累积批确定N，防止分别按microbatch均值使短样本放大。原mask/-100及新增F精确范围均由真实四features验证。

共同课程、ID顺序、mask及alpha用于两模型，单机依次训练。默认只有主14B和对照8B各一次241上限的计划，不因本文件自动开始多seed、消融或重跑。实际训练前锁定ARM64栈与16K/32K峰值内存/吞吐，当前未下载权重或测GPU性能。

## 实际部署I/O合同

Spark(aarch64/GB10)用于未来训练和模型HTTP服务；固定OpenClaw镜像实际linux/amd64，原工具、skills发现/读取、环境执行和循环继续在现有x86宿主。模型服务只使用固定chat template及标准Qwen思考/tool_call到OpenAI tool_calls的解析，**不把原生incoming消息重写成离线past-state，不过滤原生工具目录，不自行摘要或补造历史R，不引入替代Agent循环**。

新33离线投影目录有18工具，原native请求有53，实际调用5种。此差异通过保留来源原生dev验证，不能靠过滤线上工具消除。生成prompt须`enable_thinking=True`；本次CPU tokenizer测试证明False+generation_prompt会预填空think，而完整训练messages的False+非generation_prompt仍保留显式原R。这是模板合同，不是已验模型服务。

训练窗口32K。固定模型原config的max_position_embeddings40960/rope_scaling=null原字节留存；128K YaRN仅候选服务profile，原完整API最长65806加回复上限32768作保守留额98574。同层base/adapter/14B/8B采用相同上下文/RoPE/预算。ARM容器、reasoning/tool parser具体版本、长序列速度与内存待用户启动训练/验机时锁定，当前不宣称已部署。

## 如何判断训练后的模型质量

1. 先冻结dev的任务必达条件、独立D1—D5质量判据和合格规则，再做checkpoint选择。旧synthetic里的q_min=80是题给政策，不是默认生产门槛。附录开发探针覆盖阈值变化、缺阈值、评分器错误、exit0掩蔽失败、预算删失成本与来源去重，均不进入训练，也不计独立企业任务。
2. offline诊断保留来源隔离，主要发现输出结构/约束/反馈判断问题；真实原生dev才验证会话→探索→资源→试跑→修订→封装。四个冻结dev来源用于开发，四个新test来源用于初验，多个窗口/消费者不增加独立n。
3. 必须比较14B base/adapter与8B base/adapter，统一镜像、工具、材料、上下文和预算。选模以合格skill数量优先，平手比较独立Q和每合格skill成本；Q未知不补0，test不回流。记录协议误参、资源可复现、修复回归、真实skill读取/使用与最终交付。
4. 最终报告TSR、独立五维Q及组件聚类区间，TSR与Q不相乘。前期4个新test用于错误发现；若要约±10个百分点的比例精度，最保守独立样本量约97，后续可在持续隔离的原评测来源中冻结扩大测试，先核材料与血缘、再执行，不虚增当前已跑样本。本轮没有启动评测。
5. 新58相对57的整体变化包含协议监督、逐步权重与checkpoint选择；不得把全部差值归因数据量。若研究归因，按相同输入/课程分别切换F增强与aux cap；先前新经验/旧data匹配混排和等设备小时控制另列。主14B/8B比较先回答规模与总成本问题，不把所有消融变为首轮训练前置。

本轮教师候选试跑仍是NS6/6、V0/V1各5/6，CSV公式型文本处理未通过。局部序列化/工具协议可以授信，整个skill KEEP未授；新增650F不修复CSV生成器，也不伪造已经发生的业务修订。下一增量优先真实CSV失败→版本修复→同题回归→独立新输入，再扩HTML外的独立C评价与D收尾。

## 每个合格skill的总成本

统一记录恢复/标注、教师采集及失败、consumer/Q、训练、学生探索修订验证、工具与能耗/设备成本。未知账目记UNKNOWN，不记0；本轮83 provider/11 native、已知5896235 IO+1032768预留仅是已捕获教师账，不是整个项目现金。

若模型m一次性训练/接入成本T_m，平均每次完整尝试成本c_m、合格概率p_m，计划N次尝试，则`U_m(N)=(T_m/N+c_m)/p_m`。14B比8B成本更优的条件是`p14/p8 > (T14/N+c14)/(T8/N+c8)`。实际p、吞吐、耗时和现金都由后续实测填入；p=0保留成本且比率未定义。这样选的是单位合格skill收益，不仅单次速度或模型参数数。

## 数据包与复验

新58小AES delta包含实际新bank/99数组、active1260、课程/配置及审计/代码，允许同SHA复制旧21小bank作为恢复依赖；旧05—11、离线57、native57原始思考/API/SSE大包不重打。公开仅放去标识报告、schema、配置及trusted CPU工具，企业样本和token数组进入认证加密实体，密钥仍本地。

最终以ENTRY58/manifest/新实体SHA、真实解密还原逐成员SHA、还原后两profile1260四features及每step alpha/N/cap验证为准，再Git推送并从新目录冷读普通文件/完整新LFS实体。研究计划与后置交付状态分开冻结，避免自引用。原57所有文件及证据继续可取得，本文件不是训练启动器。
