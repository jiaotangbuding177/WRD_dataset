---
name: fact-ledger-drafting
description: 当用户给出现成素材并要求整理成官方汇报或一段话成稿，且数字/专名/目标口径不得改错时使用。素材→事实账本→按用途成稿→结构校验；只出题、仅描述需求或范围不明的请求走 DEFER/NEEDS_EVIDENCE，不产官方稿、不判 NO_VALUE。
---

# 事实账本成稿（fact-ledger-drafting）

候选通用机制：素材与事实/目标/约束账本 → 按用途成稿 → 字数/引用/事实缺口核对。机制为新提出候选，未经独立试跑验证复用收益。

## 适用 / 不适用

适用：用户提供自己的素材文本，要求产出官方汇报或一段话成稿；素材中的数字、单位、专名、规划目标口径必须保真；目标 Word 可能提供也可能未提供。

不适用：
- 只出题、仅描述需求、范围不明的写作请求 → 按 classify 输出 OUT_OF_SCOPE_DEFER（待澄清，非 NO_VALUE），不套用本机制产官方稿。
- 素材缺失的成稿请求 → NEEDS_EVIDENCE，不编造、不因缺输入判 NO_VALUE。
- 若未来制作课程题面转换类技能：保留原题的产品功能需求，仅剥离解题实施指导；不得机械删除功能要求。
- 不宣称任何外部独立核实：所有 user_provided 事实都标注为用户陈述、未独立核实。

## 资源索引（按需读取）

- `schemas/fact_ledger.schema.json` — 账本字段定义（fact_id、fact_type、value/unit/time/subject/qualifiers、explicit_user 与 must_keep 区分、逐字 quote 引用）。
- `schemas/draft.schema.json` — 成稿 JSON 字段定义（fact_refs、declared_numbers、word_target、word_delivery）。
- `templates/section_templates.md` — 官方汇报 / 一段话两个分支的成稿模板与措辞规则。
- `scripts/validate_pack.py` — 可执行校验器（标准库）。

## 工作流（有序）

1. 读全部用户素材原文，建账本 JSON：逐条事实给 fact_id/fact_type/出处逐字 quote；规划口径标 planned_goal；用户对成稿的明确要求标 explicit_requirement；压缩/覆盖策略记 derived_rules（basis=derived_policy_not_explicit_user），不得把「用户提到」升级成「必保逐字」。原文全量保留，缺件不虚构。完成标志：账本通过 schema 字段自检。
2. 用 classify 门控请求用途（命令见下）。非 PROCEED_* 决策：停，向用户说明 NEEDS_EVIDENCE 或 OUT_OF_SCOPE_DEFER 及缺什么。
3. 按对应模板分支写成稿 JSON：文本 + fact_refs（planned_goal 只能 as_type=planned_goal）+ declared_numbers（每数字与账本一致）+ word_target/word_delivery。完成标志：成稿 JSON 符合 draft schema。
4. 运行 validate。STRUCTURAL_FAIL：修资源/成稿后同接口重测，不删失败、不把未执行写成成功。STRUCTURAL_PASS(_SEMANTIC_REVIEW_PENDING)：逐条人工复核 NEEDS_SEMANTIC_REVIEW 项后才可交付。
5. 交付：给用户成稿文本 + 限制说明（用户陈述未经外部核实、Word 交付状态、事实缺口）。

## 公开调用方式

```bash
# 用途门控
python scripts/validate_pack.py classify --request REQ.json --report classify_report.json
# 结构校验
python scripts/validate_pack.py validate --ledger LEDGER.json --draft DRAFT.json --sources SOURCES.json --report REPORT.json
```

退出码：validate 0=结构通过 / 1=结构失败 / 2=输入错误；classify 0=已产出决策。决策与失败明细见报告 JSON 与 stdout（VERDICT/DECISION/FAIL/NEEDS_SEMANTIC_REVIEW/NOTE 行）。

字数口径：`counting_mode` 默认 `non_whitespace`（去空白字符计数），须可向用户解释；`all_characters` 为全部字符。段落计数：任意换行分段。

## 验证 / 停止 / 需澄清条件

- 校验器只做确定性结构/类型/数字/长度/引文连续性检查；成稿文字与事实的语义忠实度永远需要独立复核（NEEDS_SEMANTIC_REVIEW 项），不得当作语义已通过。
- 引文对不上原文（quote 非连续子串）：停止，回读原文修正引用，绝不改原文迁就引用。
- 必需事实/证据缺失：输出 NEEDS_EVIDENCE 并明确缺什么，不生成看似正确的业务数字。
- 范围不明（如「再做一个内容」未指明对象）：向用户澄清后再做；澄清前只标 DEFER。
- 目标 Word 未提供：只交文本并明确未写入 Word（TEXT_ONLY 状态）。

## 限制（诚实声明）

- 本机制未经独立真实试跑；复用收益未验证。
- 校验通过 ≠ 语义正确 ≠ 技能质量批准；测试通过只证明局部检查有效。
- 本技能包不含任何企业素材、制作痕迹或测试夹具；保真数据全部来自调用输入。
