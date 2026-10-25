# 全流程训练标注：证据、决定、反馈与时间

状态：指南与离线提取；未完成新全量语义标注。用户允许本助手补充必要标注，不授权启动训练。

每条记录保存以下字段，原始消息/产物不改写：

- `parent_id / episode_id / source_group / phase / role / version`：原始来源及目标角色。
- `available_at`：当前决策前已可见消息索引/资源版本；`evidence_refs`逐项定位消息、JSON pointer或文件SHA/span。
- `state_summary`：现有需求、约束、已观察工具结果；不包含未来成功信息。
- `decision`：A的reuse/new/merge/defer/no_value，C/D的retain/revise/reject/defer或明确下一阶段。
- `decision_basis`：简洁依据，引用证据；不要求公开模型内部隐藏思考或凭空生成长CoT。
- `verification_needed / next_action`：还需验证什么、下一步工具动作或阶段。
- `annotation_origin`：observed_teacher_field / evidence_derived_assistant / human_review。
- `outcome_evidence`：后续事实只放此字段，用于筛选与离线标签，不注入过去的prompt。
- `quality_status / confidence / review_status / training_admitted / publication_approved`：审核与公开分别判断。

三层判断必须区分：原教师“说了什么”、证据“支持什么”、审核者“判定是否可监督”。原review中的retain先按observed_teacher_field提取；只有资源/交付/复用/费用证据支持，才能标为可监督的正确retain。未验证的产物字段不能直接当奖励。

示意格式（全部是示意占位，不是新增训练样本）：

```json
{
  "phase": "C",
  "annotation_origin": "evidence_derived_assistant",
  "available_at": {"episode": "PLACEHOLDER", "before_message": 12},
  "evidence_refs": ["message:7", "tool_result:10"],
  "decision": "revise",
  "decision_basis": "当前已观察的资源接口检查失败，需局部修复后再次验证。",
  "verification_needed": ["修订后接口检查", "重新实际消费"],
  "outcome_evidence": null,
  "human_gold": false,
  "training_admitted": false,
  "is_illustrative_not_training_data": true
}
```

重点核验错误类型：源需求遗漏/用户纠正丢失；不真实的适用范围；把文件存在当资源正确；未实际复用就认定减负；只算成功尝试费用；修订无关资源；错误保留；应暂缓却猜答案；已经合格却继续无必要改写。

正确失败学习：保留失败动作作为已发生历史，loss=-100；后续有依据诊断、明确修复动作与正确停止可分别监督。一次工具错误不应连带删除整场后面的正确修复；一场最终成功也不意味着所有历史动作正确。

修订样本必须给真实旧版本和当时反馈；新版本的独立复现可以作为后验审核依据。旧版本未见新反馈时，不把新版当同状态DPO chosen。无法证明同条件的好坏版本只作时间有序修订SFT。

A/B/C/D标签可由原stage、产物路径和实际语义交叉确定。纯read/process不是独立决策金标；程序生成即使在exec参数内也不能忽略。D只在真实封包/停止证据存在时标注，不能把每条最终助手文本都强行标为“技能冻结成功”。

第一批校准建议至少120父样本、20%独立复核，覆盖少数决定与长上下文，报告一致率/分歧原因及阶段覆盖。后续自动规则只处理可机械验证的项，语义不确定保留needs_review。本轮恢复的候选和原标签均human_gold=false，不能因为改用新导出器就全部升级为gold。
