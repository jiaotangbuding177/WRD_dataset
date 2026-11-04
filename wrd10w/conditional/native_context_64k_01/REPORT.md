# 原生长上下文覆盖与条件64K候选（2026-10-27）

状态：`CONDITIONAL_NATIVE_64K_ONLY_NOT_READY_TO_TRAIN`。CPU候选实际编译6序列、374,534输入tokens、5,980个获批原R tokens，全部正权重0.25。独立第二tokenizer逐token直接按原字符批准范围复核PASS。本目录未进入ACTIVE；Spark位置扩展、训练内存和attention实现均未验收。

## 合同、来源与统计单位

读取双稿5.0.39／ALG-20261027-03、TRAINING_PLAN及MODEL_CONTEXT_REQUIREMENTS。原共享compile_main.py SHA256为`caa4449936c9705f17d50c09e27923d7cbd572d369e26e36bc8f8a4f27fb496f`，完整冻结副本在`tools/compile_main.frozen.py`，与原源码的diff为空。其main()没有调用；独立CPU驱动显式接收`--max-length 65536`，复用冻结的原字符监督选择函数和因果序列化器，没有替换32K常量或monkeypatch。原shared compiler／extractor／verifier／ACTIVE／双稿／训练计划／原生执行器均未修改。

固定快照只包括7个自然`completed`阶段：A_screen_narrative_01、B_make_report_02、B_revision_report_01及C_E_no_skill_01、C_E_skill_01、C_L_no_skill_01、C_L_skill_01。每个调用均核原`COMPLETE`/HTTP200回执、请求与响应SHA及SSE原`[DONE]`。C_review_report_01不在本次范围，没有读其活跃API。没有读取旧受保护数据正文。

| 阶段 | COMPLETE兼容HTTP | native实际计费调用 | 已知tokens |
|---|---:|---:|---:|
| A筛选 | 9 | 7 | 570,932 |
| B制作02 | 24 | 19 | 1,781,339 |
| B真实局修01 | 34 | 23 | 2,259,517 |
| C新例无技能 | 3 | 3 | 161,545 |
| C新例技能 | 16 | 13 | 864,484 |
| C源例无技能 | 4 | 4 | 216,325 |
| C源例技能 | 21 | 17 | 1,156,866 |
| 合计 | **111** | **86** | **7,011,008** |

这些阶段的native账本未知usage为0；现金、Codex审查/整理算力与本地CPU电量仍未知，不能当0。这也不是本项目所有历史成本。此前工作中口头初加总131是算术错误，本次逐回执实数111为准。

`raw_api_originals.zip`保存333个原request/response/receipt文件；`recovered_originals.jsonl.gz`保存111份完整原请求及当前原R/正文/动作。366个输入源pin在`SOURCE_PINS.json`，编译与独立QA结束均核未变。来源allowlist与resource ancestry均按实际job SHA核对；C单例允许是干净cohort allowlist的子集，不伪称列表必须等长。早期两次CPU proof-schema断言失败保存在`failed_cpu_attempt_02/`，没有原生会话、训练或付费模型调用。

## 长度定义与视图

`fullnative53`保留原请求的完整53工具、完整system、全部原past及当前原响应；`core7`只保留原7工具schema子集，system/past/当前响应相同。所有111例的工具投影使序列少24,960 tokens。两种视图的角色/思考包装采用现有声明过的causal-template变体；原兼容API字节单独保存，未声称这些学生序列等于底层CodeBuddy SDK最终prompt。纯text blocks按已有声明完整拼接，投影及前后SHA逐call保存，没有丢正文。

- `past`：原request当时实际送达的全部messages在当前assistant开始前的输入tokens，不含当前目标；不把更早磁盘历史或另行恢复字段补成当时未送达输入。原request中过去assistant可读R均空；未把另行恢复的过去R注入训练输入。
- `whole response`：上述past加上完整当前响应，含原R、正文、动作和原终止包装。错误与未审部分保留零loss。
- `last approved R`：最后一个获批原R token的结束位置。仅在该位置以内保留所有past，才能省略后面未来未监督completion；不补`</think>`/EOS，不宣称完整响应已放入窗口。
- 原A首请求官方non-thinking generation prefix计32,799；本轮causal变体thinking request计32,844，整响应32,968。两个不同模板/前缀计数不混作同一指标。

## 实测覆盖

分母固定111个兼容API响应；数值是本地冻结Qwen tokenizer的长度几何，不是111条独立业务或111条正训练目标。

| 视图 | 上限 | 完整past可容纳 | 整响应可容纳 | 全套已批准R可容纳（6响应） | 获批R tokens在窗口内 |
|---|---:|---:|---:|---:|---:|
| fullnative53 | 32,768 | 11/111 | 6/111 | 0/6 | 0/5,980 |
| fullnative53 | 40,960 | 40/111 | 37/111 | 0/6 | 1,390/5,980 |
| fullnative53 | 65,536 | 90/111 | 89/111 | 6/6 | 5,980/5,980 |
| fullnative53 | 131,072 | 111/111 | 111/111 | 6/6 | 5,980/5,980 |
| core7 | 32,768 | 78/111 | 75/111 | 2/6 | 5,202/5,980 |
| core7 | 40,960 | 90/111 | 90/111 | 6/6 | 5,980/5,980 |
| core7 | 65,536 | 111/111 | 111/111 | 6/6 | 5,980/5,980 |
| core7 | 131,072 | 111/111 | 111/111 | 6/6 | 5,980/5,980 |

40,960下的1,390仅表示若干已批准token在边界前，不代表任意一条响应的全部批准范围可准入，本次没有制作该截断候选。full53完整响应最大89,809，来自B真实局修；core7最大64,849。64K完整原生仍缺22个完整响应，其中B制作4个、B局修18个，不能称64K已覆盖全链。

| 阶段 | 完整响应数 | 32K整响应 | 40,960整响应 | 64K整响应 | 最大整响应 |
|---|---:|---:|---:|---:|---:|
| A筛选 | 9 | 0 | 3 | 9 | 59,544 |
| B制作02 | 24 | 1 | 5 | 20 | 69,804 |
| B局修01 | 34 | 1 | 4 | 16 | 89,809 |
| C新例无技能 | 3 | 1 | 3 | 3 | 33,081 |
| C新例技能 | 16 | 1 | 9 | 16 | 49,951 |
| C源例无技能 | 4 | 1 | 4 | 4 | 33,350 |
| C源例技能 | 21 | 1 | 9 | 21 | 53,588 |

逐call的两视图、请求/响应SHA、token序列SHA、past长度、整响应长度、各上限批准R覆盖和精确监督spans位于`coverage_per_call.jsonl.gz`；汇总为`COVERAGE_SUMMARY.csv`。完整原件、causal模板、tokenizer五文件双套SHA及独立驱动足以逐call重建token与mask。

## 已实际编译的6个条件候选

唯一批准依据仍是A_PARTIAL_REASONING_REVIEW_V3及B_PARTIAL_REASONING_REVIEW_V1；原审核身份、字符范围和SHA随候选保存，没有扩批原R语义准入。

| 原响应 | 完整past | 整响应 | 最后获批R结束位置 | 条件候选tokens | 正R tokens |
|---|---:|---:|---:|---:|---:|
| A0004 | 36,500 | 56,051 | 47,010 | 56,051 | 2,742 |
| B0007 | 40,986 | 60,229 | 55,256 | 60,229 | 2,460 |
| B0014 | 59,829 | 63,844 | 60,461 | 63,844 | 627 |
| B0016 | 63,323 | 63,802 | 63,668 | 63,802 | 73 |
| B0018 | 64,744 | 65,088 | 64,822 | 65,088 | 73 |
| B0021 | 65,510 | 65,852 | 65,520 | 65,520 | 5 |

前5条保留整响应。最后一条只省未来332个原本零loss tokens，保留全部65,510个past与全部批准R；未插入人工终止token。它距64K上限仅16 tokens，不能据训练前缀可放入推断推理整响应也能完成。

`candidate_native64k.jsonl.gz`保存完整messages、53工具、完整响应hash和条件前缀input_ids/监督spans；`arrays/`保存uint32 input_ids、int64 labels、float32 loss_weights。未审原R、全部past/system/tool观察、正文及动作均`labels=-100, weight=0`，批准原R为原token/0.25。当前本项只有R监督，原错误动作零loss保留，因此候选不套用shared主编译器对所有candidate actions统一的schema准入门；该差异显式登记，不批准动作、资源质量或整个阶段。

独立`verify_candidate.py`没有调用span选择函数，使用另一冻结tokenizer重新render，并直接从原字符批准区间推导每个token的预期label/weight；6序列全部逐token相等，18个二进制数组与原完整token前缀相等，333个ZIP成员与原字节相等、366pins未变。`INDEPENDENT_QA.json`为PASS，SHA256 `4bc68e26c8f617c610b7e81dbfc3cdac461633ad54f7bf6bad880af23b9001c1`。

这是已有3企业源、同一制作链上的6个局部响应，非6个新独立任务；与活跃A/B原R是同owner替代视图，不能叠加曝光。`OWNER_EXCLUSIVITY.json`逐条绑定原canonical response/target owner及同来源组；未来若启用native64K，必须替换同owner的core32视图，不能以新candidate_view_id再加一次曝光。相对当前core7的5,202原R tokens，新增可容纳只有778个同批已批原R tokens，没有新增语义审核、B/C/D完整信用或学生闭环证据。`contract_read_snapshot/`保存本次读取时的5.0.39双稿与两份相关计划；中央文件后续正常升级不静默改变本次条件。

## 位置扩展与Spark边界

两份冻结config确实是`max_position_embeddings=40960, rope_scaling=null`，本地已核原件每份728字节及SHA，来源为[14B pinned config](https://huggingface.co/Qwen/Qwen3-14B/blob/40c069824f4251a91eefaf281ebe4c544efd3e18/config.json)和[8B pinned config](https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/config.json)。

官方pinned模型说明给预训练原始位置基准32,768，并直接建议典型65,536用YaRN factor2.0。128K例才是factor4.0；40960不是缩放分母。[14B pinned说明](https://huggingface.co/Qwen/Qwen3-14B/blob/40c069824f4251a91eefaf281ebe4c544efd3e18/README.md#processing-long-texts)、[8B pinned说明](https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/README.md#processing-long-texts)。

由官方64K建议及同页配置形式得到的未来候选为：

```json
{"max_position_embeddings":65536,"rope_scaling":{"rope_type":"yarn","factor":2.0,"original_max_position_embeddings":32768}}
```

本轮没有启用该配置。Qwen官方提醒，截至其记录的Transformers4.52.3，实现可能实际使用`max_position_embeddings/original_max_position_embeddings`而忽略所传factor；须冻结真实运行库并核实际生效，不能只给旧40960添加factor2而称64K。[Qwen官方Transformers长上下文指南](https://qwen.readthedocs.io/en/stable/inference/transformers.html#enabling-long-context)。静态YaRN对短文本的影响同样须实测。

用户报告Spark约121GiB统一内存，本轮未远程验机。NVIDIA文档确认内存由CPU/GPU共享；官方PyTorch训练recipe默认序列2,048，没有为本项目Qwen3 14B/8B、BF16 LoRA r32和64K提供实测内存或吞吐。[Spark硬件](https://docs.nvidia.com/dgx/dgx-spark/hardware.html)、[NVIDIA训练recipe](https://raw.githubusercontent.com/NVIDIA/dgx-spark-playbooks/main/nvidia/pytorch-fine-tune/README.md)。新SM120/121 SDPA backward文档标为实验API；不能据网页有该kernel就称当前候选容器已实际调用。[NVIDIA SDPA backward](https://docs.nvidia.com/cudnn/fe-oss-apis/attention/sdpa_bwd_sm120/)。

未来必须另做位置扩展实际生效、相同模板/工具解析、SDPA forward/backward dispatch、峰值共享内存/余量、吞吐与短/长质量验证；本轮不安装torch、不下载权重、不前向、不训练。128K在长度几何上覆盖本快照，不表示设备可训或方法需要一律上128K。

## 未来训练器的logits/CE内存建议（仅计划）

两份pinned config的词表均151,936。batch1完整词表logits理论载荷为：64K BF16 19,914,555,392 bytes＝19.9146GB＝18.546875GiB；128K BF16 39,829,110,784 bytes＝39.8291GB＝37.09375GiB。相应FP32 cast分别37.09375／74.1875GiB，若BF16与FP32副本重叠存活，合计约55.64／111.28GiB。这里只是张量形状计算，Transformer激活、CE保存量、attention、优化器及实际分配峰值均另计，不能当设备实测。

HF v4.51.3 Qwen3源码先完整执行`self.model(...)`，再用`logits_to_keep`选择hidden送入`lm_head`。该参数支持整数或序列维1D Tensor：0为全量，正整数为最后N个，Tensor为指定序列位置。它为microbatch1的选择性词表投影提供官方代码依据；不同batch监督位置不同时，须按batch/seq坐标收集hidden。[官方Qwen3源码](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/qwen3/modeling_qwen3.py#L730)。

默认causal loss先`logits.float()`、labels右pad一个ignore token再取`labels[...,1:]`；任意索引logits与完整原labels不会自动对齐。未来实现必须显式只位移一次，或按冻结版本使用同形`shift_labels`，不能直接开启`logits_to_keep`后声称loss等价。[官方loss源码](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/loss/loss_utils.py#L37)。

推荐待验证的纯Torch目标为：先对齐`hidden[:,:-1]`、`labels[:,1:]`及`weights[:,1:]`，仅选择非`-100`目标所对应的前一位置hidden，再计算这些位置的**完整词表**投影与CE。定义`N`为整个optimizer step的有效shifted目标数，目标是`sum(valid_token_weight * token_CE) / N`。所有输入/未监督位置继续完整走Transformer注意力，也能经后续监督目标间接获得梯度；冻结lm_head参数不允许detach/no_grad切断hidden梯度。

PyTorch CE的`ignore_index=-100`令对应目标不贡献loss，`weight`参数是词表类别权重，不能当本项目逐token可靠性。应`reduction='none'`后逐token乘权重、求和并除有效标签数。除权重和会抵消统一0.25可靠性。[官方CE文档](https://docs.pytorch.org/docs/2.14/generated/torch.nn.CrossEntropyLoss.html)、[固定PyTorch v2.6.0 CE源码](https://github.com/pytorch/pytorch/blob/v2.6.0/torch/nn/modules/loss.py#L1039)。

梯度累积的`N`必须跨整个optimizer step预先统计，可从本地labels在forward前得到；每个microbatch以自己的加权CE和除同一个`N`再backward。不平均各microbatch均值，不再额外除累积步数。Trainer/Accelerate若自行缩放须核防止双除；未来若使用DDP，`N`需跨rank求和并补偿DDP默认梯度rank平均（本项目单Spark当前没有DDP实施）。[HF官方梯度累积说明](https://huggingface.co/blog/gradient_accumulation)。

所选hidden可分块执行`lm_head→FP32 CE→加权和`；只把所有分块loss加起来最后backward，仍可能保存全部CE中间量。纯Torch候选可对每块head＋CE使用显式`checkpoint(..., use_reentrant=False)`重算，未来须实测与原完整masked CE的loss及LoRA梯度在数值容差内相等。[PyTorch checkpoint源码和说明](https://github.com/pytorch/pytorch/blob/v2.6.0/torch/utils/checkpoint.py#L314)。这项建议不假定Liger/CCE的ARM64＋GB10 kernel已支持，不解决长上下文attention本身的内存；位置扩展、SDPA、前反向峰值与吞吐仍分别待验。当前没有训练器代码变更、torch安装、模型前向或训练。

## 训练长度与推理输出预留分开

逐111份原API请求核实，其`max_tokens`全部为32,768（非仅外层名义预算）。若未来服务严格要求`serialized_prompt_tokens + requested_max_tokens <= total_context`，64K训练序列可放入不等于同预算推理请求合法。

| 输入视图 | 总context | 申请输出tokens | 严格预留后可接请求 |
|---|---:|---:|---:|
| fullnative53 | 40,960 | 32,768 | 0/111 |
| fullnative53 | 65,536 | 32,768 | 11/111 |
| fullnative53 | 131,072 | 32,768 | 111/111 |
| core7 | 40,960 | 32,768 | 16/111 |
| core7 | 65,536 | 32,768 | 78/111 |
| core7 | 131,072 | 32,768 | 111/111 |

表中prompt使用causal thinking request长度；`SERVING_HEADROOM.json`保存逐call来源SHA对应数据。full53最大request89,204，另预留32,768后121,972。A首请求沿原官方non-thinking计32,799＋32,768＝65,567，超64K 31 tokens；用未来声明causal thinking前缀则32,844＋32,768＝65,612，超76。B0021 causal thinking input65,513，64K仅余23输出tokens，原完整响应需65,852。对实际服务须使用其真实模板/tokenizer/特殊token开销重新测量。

此处的128K全接仍只是本快照长度几何，不证明位置扩展、完整执行或Spark服务可用。未来可比较总context128K/YaRN factor4（保持32,768输出上限）、训练主64K并对少量80—96K真实序列另做条件profile；也可研究四学生组同一server统一按剩余context裁减`max_new_tokens`，但后者实质改变公共预算，必须显式申明和四组一致。当前没有选定或实现任一方案，原native32,768/1800秒及Teacher继续保持；最终student profile由独立位置/内存/解析/公平预算验证决定。

官方版本行为另已核清：vLLM v0.10.2/v0.11.0在兼容chat预处理时，对显式`max_tokens`先核输入＋申请输出是否超过`max_model_len`，超出即ValueError；后续`get_max_tokens()`虽取剩余窗口最小值，调用顺序仍不能挽救前面的拒绝，默认不自动缩减这个显式超限请求。`truncate_prompt_tokens`是裁输入，不能用来冒充保留完整past的输出clamp。[vLLM v0.11校验](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/entrypoints/openai/serving_engine.py#L611)、[v0.10.2校验](https://github.com/vllm-project/vllm/blob/v0.10.2/vllm/entrypoints/openai/serving_engine.py#L611)、[v0.11取最小值函数](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/entrypoints/utils.py#L177)、[chat调用顺序](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/entrypoints/openai/serving_chat.py#L217)。本项目未来服务版本未定，仍须对冻结实际版本核验。

HF4.51.3 `generate`的`max_new_tokens`优先于`max_length`，会设总长度为输入长度加新token数，显式请求不会自动按模型`max_position_embeddings`安全缩减；模型位置边界的停止器警告也不是服务准入保障。[HF长度处理](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/generation/utils.py#L1473)、[HF停止器](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/generation/stopping_criteria.py#L51)。

OpenClaw v2026.9.5的`contextWindow/contextTokens`属于模型目录及运行预算元信息，不会改变模型RoPE或服务物理窗口。[同版context解析](https://github.com/openclaw/openclaw/blob/v2026.9.5/src/agents/context-resolution.ts#L176)、[context guard](https://github.com/openclaw/openclaw/blob/v2026.9.5/src/agents/context-window-guard.ts#L28)。其原生compaction可按窗口/reserve估算触发，并在overflow后恢复；虽然磁盘保留全文，后续模型看到summary＋保留尾部，不能据磁盘全文冒称完整旧past仍逐字送达。[同版compaction文档](https://github.com/openclaw/openclaw/blob/v2026.9.5/docs/reference/session-management-compaction/compaction.md#L7)。未来四学生组必须冻结相同真实服务、模板、工具和context元信息/输出预算；本项没有借元信息或compaction规避当前长past限制。

## 数据准备建议与充分性

证据支持并行保留三个清楚标识的银行：完整原生53工具长视图；声明过的core7学生接口视图；独立作者且能回原证据的状态重构视图。按实际应用与可验证位置/内存选择目标视图，同一原owner择一曝光。原32K主入口保持；条件64K数据由独立目录保全，需真实硬件/位置验证以及同轮双稿审核后才可能讨论新的准入。

64K解决本批获批R的原工具目录长度障碍，但完整53工具过程还有89,809-token输入/输出，后续局修/评审信用仍待核。下一步以已结束C链的实际版本/反馈进行独立审核，按来源/阶段/版本平衡补真正目标；不能靠复制epoch、切多个窗或多工具目录tokens充足量。当前条件集远未达到≥50干净来源群、≥12机制族、≥2,000非平凡主目标和≥100万主监督tokens的既定工程准备线；达到数量也不证明学生全链能力。没有新增效果/泛化/训练收益结论。

本轮新增实证仅为冻结原请求覆盖、条件CPU数组和逐token QA；官方资料支持位置扩展候选，不替代Spark实测。共享中央记忆与新双稿由root在真实首条C链结束安全点统一登记，本子任务不竞争改写。
