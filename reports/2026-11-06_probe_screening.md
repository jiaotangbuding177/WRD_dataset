# v2 权重验收与 12 探针筛查（2026-11-06）

## 验收（eval_wrd58.py audit）
- "status": "pass"，18/18（代码、COURSE58/CONFIG58 pin、两份日志含末步 loss、12 个 v2 adapter SHA 全过）。

## 基座一致性（--check-base-parity）
- 8B 与 14B checkpoint-0 输出与纯基座 exact 一致（exact: true），checkpoint-0 可作对照。

## 探针筛查结果（每尺寸 6 检查点 × 12 道固定探针）
| checkpoint | 0 | 26 | 80 | 134 | 188 | 241 |
|---|---|---|---|---|---|---|
| 8B passed/12 | 8 | 8 | 7 | 6 | 7 | 8 |
| 14B passed/12 | 8 | 9 | 6 | 6 | 5 | 6 |

- 逐题明细（field_pass、adapter SHA、token 数、耗时）：wrd58_probe_8b.jsonl / wrd58_probe_14b.jsonl（各 80 行，已提交本分支）。
- 8B ���平（6–8，241 回到 8）；14B 峰值在 26（9/12），此后走低至 188 的 5/12。
- 探针通过数为离线短诊断信号，不等于原生 dev 集结论；候选筛选由用户按逐题表现完成。
