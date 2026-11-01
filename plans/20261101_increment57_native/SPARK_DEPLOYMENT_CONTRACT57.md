# Spark模型服务与固定原生执行环境

这是候选部署合同与验机清单，尚未部署、未下载权重、未启动模型/训练，也未验证128K速度、统一内存峰值或质量。

## 执行位置

固定OpenClaw镜像`sha256:97a0f55bec1ef293c15ddd5a17cc843050387bd2369dcf2fd388b1afd40810a2`实际为**linux/amd64**。现有x86宿主继续运行同一固定镜像、工具、skills发现/读取和原生会话循环；Spark为aarch64，负责ARM64兼容的训练栈与学生模型HTTP推理服务。OpenClaw通过HTTP调用Spark，避免为迁移算力改变工具执行环境。当前amd64镜像不表述为可原生安装到Spark ARM的镜像，也没有安排替代Agent循环。

## 模型配置、训练窗口与服务窗口

只下载了精确revision的两个728字节config，未下载weights：

| 模型 | revision | config SHA256 |
|---|---|---|
| Qwen3-14B | `40c069824f4251a91eefaf281ebe4c544efd3e18` | `e73c3664ca09b10a673fef0c22e8a6b456201d49bd4713c9691f775720e8857a` |
| Qwen3-8B | `b968826d9c46dd6066d109eabc6255188de91218` | `f7c4eadfbbf522470667b797a3c89be2524832d2d599797248dc304fff447c30` |

两份原config均为`max_position_embeddings=40960`、`rope_scaling=null`，原字节复制并附receipt。模型卡区分32768原生上下文与通过YaRN扩展到131072；这不是文件已开启长上下文的证明。[14B官方模型卡](https://huggingface.co/Qwen/Qwen3-14B#processing-long-texts)、[8B官方模型卡](https://huggingface.co/Qwen/Qwen3-8B#processing-long-texts)。

当前完整原API审计最长序列65806；按旧单次最大回复32768再保守留额，总上界98574，所以拟锁定**131072（128K）服务profile**。65806是已审完整序列长度，这个加法是保守留额，不冒充精确单次输入token计数。

候选服务覆盖参数为`rope_type=yarn`、`factor=4.0`、`original_max_position_embeddings=32768`、`max_model_len=131072`，与两份官方模型卡的长文本配置一致。它只作为模型服务的单独候选override，不修改原config副本或241步训练配置。两者的共同SFT窗口仍≤32768，不能把静态训练长度当完整动态rollout长度。

官方也提示静态YaRN可能影响短文本表现，因此在同一个服务profile层内，base/adapter、14B/8B必须使用相同context、RoPE设置、回复cap和任务预算；短/长profile分层报告，不把跨profile差异当adapter收益。[14B说明](https://huggingface.co/Qwen/Qwen3-14B#processing-long-texts)、[8B说明](https://huggingface.co/Qwen/Qwen3-8B#processing-long-texts)。

## 未来验机项目

先选定并记录Spark ARM64模型服务栈、容器摘要及CUDA/kernel版本，再实测长序列接收、prefill/decode吞吐、统一内存/KV峰值，以及reasoning/tool_calls解析、完整SSE捕获、原生续跑/owner和预算元数据接线。只在验机后确定实际启动参数与速度/内存结论；本次不启动服务、不安装软件、不改在途producer/consumer。

## 历史thinking可见性的研究模板变体

Qwen3官方建议多轮历史只保留最终输出，不保留历史thinking；官方模板会实施该历史策略。[14B Best Practices](https://huggingface.co/Qwen/Qwen3-14B#best-practices)、[8B Best Practices](https://huggingface.co/Qwen/Qwen3-8B#best-practices)。

本研究为保留用户的真实过程，采用已经冻结的显式原provider R与past-only状态模板变体；它不是官方默认请求或原native历史的等价副本。训练input_ids、R原文和241步配置不重模板化、不删除。未来serving须先明确并复现同一可见状态、工具序列和R可见性，再与官方历史策略做训练后的受控对照；同层base/adapter、14B/8B保持相同context/预算。该对照和接口接线尚待验证，不据此声称ARM长程质量已实测，也不安排替代原生Agent循环。
