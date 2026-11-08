# 2026-11-08 接续：长输入终止异常与技能制作

当前仅验证skills生成，消费继续为0。本文件覆盖旧执行单中必须四臂全部通过才运行制作的安排。无需重跑已完成的训练验收或144条短探针。

## 已知结果与处理

同事报告8B checkpoint-26在约66023 tokens重复填充输入下，thinking ON/OFF两次均耗满32768输出，`finish_reason=length`；OFF墙钟76.8分钟。同事报告8B-0臂通过，prefill、SSE、用量和工具协议已有通过证据；两种thinking各自严格配对的原始请求尚待审核。

这条报告是该候选在这两次长输入试验中的明确终止失败，当前将8B-26置HOLD，不派发完整技能制作，不再重复相同32K输出测试。全部既有费用和错误保留。原始请求、响应、实际脚本和服务参数尚未回到本交接审核侧，状态按USER_REPORTED登记，不写成已独立验过原件。

原smoke给重复填充后的简答请求32768输出预算，且将自然停止与接口容量绑在一起，这项试验设计已纠正。新长容量探针默认只给64输出，允许64/128/256；`length`只说明在这个短输出预算内未停止，**接口容量通过与自然停止分开记录**。新的短预算length结果不追认成自然收尾成功，也不覆盖两次旧32K失败。已通过的旧原始回执保留，旧fail不自动改pass。

## 同事现在做什么

1. 保存所有已有回执。更新本分支，保留旧运行目录和真实服务参数，继续使用同一镜像/基座/adapter，不改stop字符串、EOS、采样或模板来制造通过。
2. **8B-26暂停**，不要再切thinking重跑长测试。把两次原始请求、完整响应/流、实际脚本、服务启动参数、adapter SHA、token用量与耗时复制到工具主机的 `local/diagnostic_evidence/`。这不是要求再次请求模型。
3. **8B-0先制作**。已有合法容量与原生工具PASS回执可直接复用。入口现在只检查目标臂与当前尺寸；8B-26失败或未运行14B不会阻塞8B-0。若旧失败汇总丢失了8B-0的逐臂容量行，仅补下面的有界容量证据，不重复32K输出：

   ```bash
   # Spark 8B服务保持原配置在线，包根目录执行
   python3 spark/smoke_wrd58.py 8b --arm 0 --context 131072 --long-input --out receipts/smoke_8b_bounded.json
   ```

   将这个JSON复制到工具主机 `local/spark_receipts/smoke_8b_128k.json`，**先将该位置已有原件移到带时间的备份路径**。旧文件与旧费用保留；服务启动日志仍用同配置真实 `serve_8b_128k.log`。若原生工具烟测还缺，只对8B-0执行原300秒/1024输出的技术烟测。随后在工具主机执行：

   ```bash
   # 未投递时才执行stage；已有stage直接保留复用
   python3 local/run_native58.py stage --materials materials
   python3 local/run_native58.py producer --arm wrd58-8b-0 --profile yarn128
   ```

4. **14B-0与14B-26按各自证据继续**。切换同一固定vLLM镜像的14B服务；缺容量证据时，新的有界命令为：

   ```bash
   python3 spark/smoke_wrd58.py 14b --arm both --context 131072 --long-input --out receipts/smoke_14b_bounded.json
   ```

   同样保全原件后将新JSON投递到工具主机对应 `smoke_14b_128k.json`，补缺失的目标臂原生技术smoke。两臂分别准入，已通过的一臂可继续，失败不拖住另一臂。工具主机执行：

   ```bash
   python3 local/run_native58.py producer --arm wrd58-14b-0 --profile yarn128
   python3 local/run_native58.py producer --arm wrd58-14b-26 --profile yarn128
   ```

5. 制作仍按原冻结提示、原生工具和1800秒/24请求/单回复32768预算运行。**这次只改变无业务价值的容量烟测预算，不暗改真实制作预算。** 原始技能、资源自测、修订、终态和全部成本照常保留。没有足够证据的臂保留HOLD，不补造技能。模型若在真实制作中耗尽预算，保留实际过程和账单，不以截断当正常结束。
6. 用 `python3 local/package_return58.py --out wrd58-generation-return.zip` 一次回传技能与完整证据。脚本包含 `local/diagnostic_evidence/` 和当前候选状态；8B-26未执行会明确登记HELD，不冒作完成。回包带同名`.sha256`。

## 后续定位需要什么

先审核已有两次原件：实际adapter SHA、thinking模板参数、temperature/top_p/top_k、`ignore_eos`、stop/EOS配置、原始生成尾部与是否重复。不要仅凭解码文本看不到特殊符号就断言没有产生过EOS。76.8分钟与旧上传脚本300秒超时不同，实际改动脚本也须保存，用于绑定运行条件，不推测同事用了哪套配置。

已核本地训练合同：26只经过401条contract，过程课程从27开始；contract已有401个151645停止监督，不能称没教EOS。共同SFT长度上限32768，约66K属于扩窗条件。原生应在`im_end`结束，不以`</think>`或人为字符串截断冒充修复。后续若需要长度定位，另行按同任务/同采样/小输出预算做成对诊断，不自动扩成批量重训或多轮长生成。

Qwen官方说明原生32K与YaRN128K，并提示静态YaRN可能影响其它长度下的行为；这支持把扩窗效应列作待定位因素，不能直接替本次异常确定根因。[Qwen3-8B模型卡](https://huggingface.co/Qwen/Qwen3-8B)。vLLM的EOS与最大输出预算有独立参数，当前诊断应保留其实际值。[vLLM SamplingParams](https://docs.vllm.ai/en/stable/api/vllm/sampling_params/)
