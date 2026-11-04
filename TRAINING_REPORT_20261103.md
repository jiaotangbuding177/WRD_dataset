# WRD audit58 训练结果报告（2026-11-03）

## 概要

audit58 计划（plans/20261102_final_training_audit58/）的两个训练全部完成：

| 模型 | 状态 | 时间窗（UTC） | 用时 | 检查点 |
|---|---|---|---|---|
| Qwen3-8B（对照） | rc=0，241/241 步 | 11-02 05:51 → 11-02 20:21 | 14.5h | 6/6 |
| Qwen3-14B（主） | rc=0，241/241 步 | 11-02 20:21 → 11-03 19:17 | 23h | 6/6 |

总计 37.4 小时，482 个 optimizer 更新，零 OOM、零 Traceback、零人工干预。

## 数据恢复链（训练前置，全部 SHA pin 校验通过）

restore_checkpoint05 → merge_delta06..10 → restore_package11 → restore_v58 → verify_restore58 (PASS)。

- BASE10 三 pin 全匹配：TRAINING_MANIFEST 9aace2dc…、PAYLOAD_MANIFEST 88e0f8b6…、ARRAY_INDEX10 712c96c0…
- 关键方法：上游合并在 Windows 上生成，`Path.write_text()` 文本模式写入 CRLF；Linux 复现需 sitecustomize monkeypatch 强制 \r\n（WRD_FORCE_CRLF=1），否则清单 SHA 不合
- 激活根 active58/：COURSE58.json sha 4ca57466…、CONFIG58.json、ACTIVE_DATASET_MANIFEST58/57 sha 8141747…
- 课程契约（budget_projection）：401 contract exposures/26 updates (acc≤16) + 859 process exposures/215 updates (acc≤4)；1260 唯一目标、295478 正 tokens；变量分母 CE（无按累积数或权重和归一）

## 训练配置（CONFIG58）

- 基座：Qwen3-14B @ 40c069824f4251a91eefaf281ebe4c544efd3e18；Qwen3-8B @ b968826d9c46dd6066d109eabc6255188de91218；bf16 冻结
- LoRA：r=32, alpha=64, dropout=0.05，target q/k/v/o/gate/up/down；embed_tokens + lm_head 冻结；8B 可训练 87,293,952 (1.05%)、14B 可训练 128,450,560 (0.86%)
- AdamW lr 5e-5, betas (0.9,0.999), eps 1e-8, wd 0.01, max_grad_norm 1.0；constant_with_warmup(3)；seed 20261101
- microbatch 1、max len 32768、无截断、无 packing、无 retemplatization
- 损失：每 optimizer 步 loss = Σ(effective_weight_i × CE_i) / N_step；effective weights 经 objective_adapter58.prepare_optimizer_step 校验（含辅助 alpha 缩放仅作用于 synthetic pool）

## 硬件与工程

- DGX Spark（GB10 统一内存 121.7GB），Docker 容器内训练（torch 2.14.1+cu130 / transformers 4.57.1 / peft 0.18.0）
- **分块 CE**（chunk=2048，torch.utils.checkpoint 序列维分块重算）：整张 fp32 log_softmax（32K×152K 词表 ≈20GB）在 AdamW 动量存在时必然 OOM；分块后逐位一致，峰值额外显存 ~1.2GB/chunk
- 实测显存下限：8B 全程 ≥10.1GB 空闲；14B 全程钉在 ~1.1GB 空闲（contract 阶段 16 微批大步为最险窗口，平安穿过）
- 期间两次 SSH 断连（最长约 2h），训练不受影响（docker exec -d 独立运行 + 容器内日志落盘）

## 产物清单

- `out58_8b/checkpoint-{0,26,80,134,188,241}/`：LoRA adapter（adapter_model.safetensors ~333MB + adapter_config.json + train_meta.json）；checkpoint-0 为 SFT 前基线
- `out58_14b/checkpoint-{0,26,80,134,188,241}/`：同上
- `logs58/launcher.log`、`logs58/train_8b.log`、`logs58/train_14b.log`：完整运行日志
- 推理加载：从 HF 加载对应 revision 基座 → peft 挂载 adapter（标准用法）

## SHA256（终态检查点 adapter_model.safetensors）

见 `TRAINING_SHA256_20261103.txt`（全部 12 个检查点 + 日志）。

## 边界说明

训练完成 ≠ 效果验证。各检查点在下游任务上的评估（PLAN.md FROZEN_DEV_CLOSED_LOOP_TSR_Q_COST_PARETO_NO_TEST_SELECTION 候选选择）尚未执行；训练 loss 绝对值（含负权重惩罚项，故为负值）不作为效果证据。
