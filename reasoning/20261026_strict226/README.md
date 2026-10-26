# 原226隔离确认与可见性更正

用户2026-10-26确认：**继续隔离原226来源，保留原评测边界**。不启动训练。

[固定范围](SCOPE_CONFIRMATION.json) · [当前候选数量](DIRECT_SOURCE_CANDIDATE_REPORT.json) · [最终训练准入清单](FINAL_TRAINING_MANIFEST.json) · [更新后的完整训练计划](../../plans/20261025_reasoning_distillation/README.md)

最终训练清单准入为0、默认数据集为空。原226正文、答案、反馈及其衍生资源不能用于训练、补注回流、checkpoint选择或门槛校准；后来改标evolution不改变这一边界。

## 本轮实际变化

全部1763原生会话追加可见性审计，重点复查651个未决会话。扫描支持`requests/text`及串接JSON，区分真实正文、路径指针、实际读到的路线资源和仅文件池可用。旧严格候选中确认1个prepare窗口读到了原226正文，已撤出；公开候选没有该项。路径指针的一次首轮过度判断已经撤回，详细更正见[正文正证据override](STRICT_SOURCE_VISIBILITY_OVERRIDES.json)，未决项不一概称污染。

| 直接来源候选 | 窗口 | owned目标 | 候选监督tokens | ≤16K窗口 | ≤32K窗口 |
|---|---:|---:|---:|---:|---:|
| 本地沉淀主体 | 275 | 3897 | 476418 | 9 | 275 |
| 公开沉淀主体 | 85 | 1257 | 198769 | 7 | 85 |
| 本地Actor辅助 | 411 | 5029 | 2050921 | 164 | 411 |
| 公开Actor辅助 | 297 | 3823 | 1624017 | 128 | 297 |

这些是候选过程窗口，尚未证明全部资源传递隔离，不是完整自主任务或最终训练准入。公开`data/*.zero_loss.jsonl.gz`保留与旧公开数组相同的input_ids，active span、target owned span及监督计数均为0；候选原span/target元数据另存`candidate_original_*`，不准绕过当前manifest恢复正loss启动训练。旧v4数组和约739MB加密原件保留作历史证据。

另回收9个受控通用发现前缀：9目标、40103输入tokens、279候选监督tokens，全部≤16K，公开0。仅7次列目录和2次文件发现，保护路线read动作、返回及后续内容全部排除。独立逐条同模板重渲染、14B/8B实际编码解码、mask和owner核验通过；见[PREFIX_RECOVERY_REPORT](PREFIX_RECOVERY_REPORT.json)及[独立QA](INDEPENDENT_PREFIX_QA.json)。这些片段不增加完整领域任务数。

[可见性报告](VISIBILITY_REVIEW.json)另找到91个只观察到evolution正文的会话入口，以及119条相应原结构化决定记录。记录与原会话重叠，资源血缘尚未证明，不相加当独立训练样本；没有自动释放训练准入，也没有合成教师思考或工具结果。

## 受控增量数据

`controlled/wrd-strict226-evidence-v5.tar.gz.aesgcm`提供本轮全部受控证据索引、9个原生前缀、原始核验报告和包内逐成员manifest。它使用v4原本机密钥和不同的新nonce，未将密钥或私盐上传Git。解密接口沿用`../20261025/tooling/encrypted_delivery.py`；解密后先核包内manifest及[加密回执](CONTROLLED_DELTA_ENCRYPTION_REPORT.json)。无需重下载旧大包以取得本轮增量。

下一步先核清91个入口的资源血缘，再从获准独立来源的原记录补齐A筛选、C取题及真实修订/收尾证据。若现存干净原轨迹不足，须如实报告缺口；通用补注不能冒充已执行的完整闭环。14B主、8B对照的训练参数建议和按合格技能计全成本的验收保持，完整自主能力仍需新独立来源的端到端实测。

本轮只做离线CPU审计、数据编译和Git交付，没有加载模型权重、使用GPU、启动训练或新增教师/Actor/Judge/原生业务会话。
