# WRD58 在同一次请求内解除推理复读

## 处理位置

在 Spark 的 vLLM 采样器加载 `wrd58_reasoning_guard.py`。只看当前 Qwen3-14B 助手段的已生成 token。正常长推理走原采样。思考段尾部出现至少四个完全相同的周期且总跨度至少 64 tokens 时，只屏蔽下一轮重复的起始 token 一步，随后由模型继续推理。处理后若新生成的 token 再满足重复条件，采样器在当前请求中采出 Qwen3 的 `</think>`，然后恢复原采样。工具调用开始、正常关闭思考、或非 thinking 的提示前缀都会关闭本请求的检测。文件写入、试跑、修订、审核和试用仍由原生 OpenClaw 执行。

两次动作都只改变当前请求的采样分数。已生成内容、输入、工具定义、工具回执和透明中继按原样保留。候选不设置固定推理预算，不改任何阶段的输出上限。重复阈值只用于检测完全重复。语义近似、间隔较大的循环及质量表现待真实运行观察。

## Spark 接入候选

候选按 vLLM 0.31 的 legacy model runner 接口编写。当前交接使用 NVIDIA `26.10.pre1-py3`，先在现有 Spark 容器做只读接口核验。以下命令的 `CONTAINER` 设为 Spark 上当前 vLLM 容器名。

```bash
docker exec "$CONTAINER" python -c 'import inspect, vllm; from vllm.v1.sample.logits_processor import AdapterLogitsProcessor as A; print(vllm.__version__); print(inspect.signature(A.__init__)); print(inspect.signature(A.new_req_logits_processor))'
docker exec "$CONTAINER" vllm serve --help=all | grep -E -- 'logits-processors|async-scheduling'
```

确认真实接口后，在后续 Spark 启动的 `docker run` 参数中将 `wrd58_reasoning_guard.py` 所在目录只读挂到 `/opt/wrd58-guard`，让该目录进入容器 `PYTHONPATH`，设置 `VLLM_USE_V2_MODEL_RUNNER=0`。在原 `vllm serve` 参数中加入以下选项。保留已核验镜像、模型 revision、LoRA 三个别名、原采样和解析器。旧服务在途请求继续沿用旧启动配置。

```bash
--no-async-scheduling --logits-processors wrd58_reasoning_guard:Qwen3ReasoningGuard
```

这里给出的是接入差异。Spark 真实预发布镜像的 import、实际采样器和 Qwen3/Hermes 工具输出仍要由同事读回验证，不能用正式版的版本号替代现场检查。该处理器在引擎初始化加载，适用于之后进入服务的新请求。

## 验收

- CPU 张量检查已覆盖 4,000 个正常生成位置、短重复、单 token 屏蔽、继续有效推理、再次循环后只采出 `</think>`，以及工具正文、关闭 thinking、已有掩码均不受干预。读取 F 批旧 SSE，在 79,801 字符的 reasoning 中观察到 226 字符的片段连续重复四次。文本证据用于确认症状，CPU 张量检查用模拟 token。
- 下一条正常排产沿用同一条路线和原材料。若触发，检查同一 `response_id` 的 SSE 在思考结束后继续出现真实 `tool_calls`，以及后续 `write`、资源试跑及工件。触发计入回执，验收依据是实际工件和原有功能判据。无需为保护机制重新派发该请求。

[现行 Spark 启动](https://github.com/jiaotangbuding177/WRD_dataset/blob/ff2d5c82b713d52ae783b2adbb2ad440d1b44145/full_evolution/20261109/execution/spark/serve_wrd58.sh) · [vLLM 0.31 legacy 处理器源码](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/v1/sample/logits_processor/__init__.py) · [冻结 Qwen3 模板](https://huggingface.co/Qwen/Qwen3-14B/blob/40c069824f4251a91eefaf281ebe4c544efd3e18/tokenizer_config.json)
