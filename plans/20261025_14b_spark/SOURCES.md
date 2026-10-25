# 官方来源与事实边界

核对日期2026-10-25，Asia/Shanghai。本目录为公开计划，不含企业来源材料。下列资料支持模型/工具的公开事实；本研究参数、阈值、计数协议与预算属于方案建议，不能从文档存在推断已在本机验证。

| 来源 | 支持内容 |
|---|---|
| [Qwen3-14B官方卡](https://huggingface.co/Qwen/Qwen3-14B) / [API](https://huggingface.co/api/models/Qwen/Qwen3-14B) | 文本稠密模型、约14.8B、原生32768、精确revision和参数 |
| [Qwen3-8B官方卡](https://huggingface.co/Qwen/Qwen3-8B) / [API](https://huggingface.co/api/models/Qwen/Qwen3-8B) | 约8.2B对照、原生32768、精确revision和参数 |
| [锁定14B配置](https://huggingface.co/Qwen/Qwen3-14B/raw/40c069824f4251a91eefaf281ebe4c544efd3e18/config.json) | 40层及投影维度，LoRA参数公式依据 |
| [锁定8B配置](https://huggingface.co/Qwen/Qwen3-8B/raw/b968826d9c46dd6066d109eabc6255188de91218/config.json) | 36层及投影维度，LoRA参数公式依据 |
| [锁定14B分词模板](https://huggingface.co/Qwen/Qwen3-14B/raw/40c069824f4251a91eefaf281ebe4c544efd3e18/tokenizer_config.json) | 工具格式、thinking开关、EOS；实际目标mask仍待编译 |
| [NVIDIA Spark微调playbook](https://github.com/NVIDIA/dgx-spark-playbooks/blob/main/nvidia/playbook-pytorch-fine-tune/README.md) | 25.11-py3镜像与HF库组合起点；非本项目性能实测 |
| [NVIDIA PyTorch25.11](https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-25-11.html) | 容器CUDA13.0.2、PyTorch构建与依赖约束 |
| [CUDA13.0.2发布说明](https://docs.nvidia.com/cuda/archive/13.0.2/cuda-toolkit-release-notes/index.html) | 驱动兼容背景；不替代GB10算子测试 |
| [Spark硬件](https://docs.nvidia.com/dgx/dgx-spark/hardware.html) | ARM、统一内存与带宽；推理宣传值不当BF16训练吞吐 |
| [Spark已知问题](https://docs.nvidia.com/dgx/dgx-spark/known-issues.html) | nvidia-smi及统一内存统计边界 |
| [TRL0.25.1 SFT](https://huggingface.co/docs/trl/v0.25.1/en/sft_trainer) | prompt/completion、tools与loss mask接口；默认截断需避免 |
| [PEFT LoRA](https://huggingface.co/docs/peft/en/developer_guides/lora) | 冻结基座与显式目标模块 |
| [bitsandbytes安装矩阵](https://huggingface.co/docs/bitsandbytes/main/en/installation) | ARM64/SM121量化支持需按发布版/ABI验证，不作主方案必需依赖 |

本轮只读获取公开配置/分词器资产并核哈希，没有下载模型权重、安装库、运行tokenizer、接入Spark或进行训练。镜像digest、完整依赖锁、运行时attention后端、数据token量、吞吐/峰值内存/电耗/质量/回本全部待测。
