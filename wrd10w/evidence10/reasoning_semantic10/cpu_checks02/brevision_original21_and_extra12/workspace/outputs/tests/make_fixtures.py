#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_fixtures.py — 生成明确虚构的测试夹具（非真实业务来源）。

所有素材均为虚构样例（蓝星云课堂/蓝星教育/北辰研究院等），专用于测试技能公开接口。
B1a/B1b 的边界文本通过导入技能公开的 count_chars 函数精确构造，保证口径一致。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_SCRIPTS = os.path.join(HERE, "..", "skill", "scripts")
sys.path.insert(0, os.path.abspath(SKILL_SCRIPTS))
from validate_pack import count_chars  # noqa: E402

FIX = os.path.join(HERE, "fixtures")
os.makedirs(FIX, exist_ok=True)

SOURCES = {
    "schema": "wrd-sources-v1",
    "_note": "本文件素材为测试虚构样本，非真实业务来源",
    "sources": [
        {
            "source_id": "demo_src_A",
            "messages": [
                {"message_id": "demo_src_A:msg_1", "role": "user",
                 "content": "蓝星云课堂平台经过一年的研发，从原型走向产品。试点覆盖12个班级。实测显示，教师备课时间平均每周节省约5小时，教学效率提升30%。推广方面，平台已在云星市40所学校上线，累计服务师生2万人。"},
                {"message_id": "demo_src_A:msg_2", "role": "user",
                 "content": "请从建设成果、推广等角度，把下面素材整理成一份官方汇报，用于内部汇报场景。"},
                {"message_id": "demo_src_A:msg_3", "role": "user", "content": "600字以内"},
            ],
        },
        {
            "source_id": "demo_src_B",
            "messages": [
                {"message_id": "demo_src_B:msg_1", "role": "user",
                 "content": "蓝星教育合作与到款规划：预计五年总目标500万元。2027年完成首批试点校签约；2028年覆盖100所学校。底线目标300万，挑战目标500万，激进目标700万。合作单位包括北辰研究院、南江实验学校。"},
                {"message_id": "demo_src_B:msg_2", "role": "user",
                 "content": "帮我把这段合作规划整理成一段话，目标口径保持预计，不要写成已经完成。"},
            ],
        },
    ],
}

N1_FACTS = [
    {"fact_id": "F001", "fact_type": "user_statement", "claim": "试点覆盖12个班级",
     "value": "12", "unit": "个班级", "subject": "蓝星云课堂平台试点覆盖", "qualifiers": None,
     "explicit_user": True, "must_keep": False,
     "evidence_refs": [{"source_id": "demo_src_A", "message_id": "demo_src_A:msg_1", "quote": "试点覆盖12个班级"}]},
    {"fact_id": "F002", "fact_type": "user_statement", "claim": "教师备课时间平均每周节省约5小时（实测口径）",
     "value": "5", "unit": "小时", "subject": "教师备课时间每周节省(实测口径)", "qualifiers": "约/实测显示",
     "explicit_user": True, "must_keep": False,
     "evidence_refs": [{"source_id": "demo_src_A", "message_id": "demo_src_A:msg_1", "quote": "教师备课时间平均每周节省约5小时"}]},
    {"fact_id": "F003", "fact_type": "user_statement", "claim": "教学效率提升30%（实测口径）",
     "value": "30", "unit": "%", "subject": "教学效率提升(实测口径)", "qualifiers": "实测显示",
     "explicit_user": True, "must_keep": False,
     "evidence_refs": [{"source_id": "demo_src_A", "message_id": "demo_src_A:msg_1", "quote": "教学效率提升30%"}]},
    {"fact_id": "F004", "fact_type": "user_statement", "claim": "平台已在云星市40所学校上线",
     "value": "40", "unit": "所", "subject": "云星市上线学校", "qualifiers": None,
     "explicit_user": True, "must_keep": False,
     "evidence_refs": [{"source_id": "demo_src_A", "message_id": "demo_src_A:msg_1", "quote": "云星市40所学校上线"}]},
    {"fact_id": "F005", "fact_type": "user_statement", "claim": "累计服务师生2万人",
     "value": "2", "unit": "万人", "subject": "累计服务师生", "qualifiers": None,
     "explicit_user": True, "must_keep": False,
     "evidence_refs": [{"source_id": "demo_src_A", "message_id": "demo_src_A:msg_1", "quote": "累计服务师生2万人"}]},
    {"fact_id": "R001", "fact_type": "explicit_requirement", "claim": "从建设成果、推广等角度整理成一份官方汇报",
     "value": None, "unit": None, "subject": None, "qualifiers": None,
     "explicit_user": True, "must_keep": False,
     "evidence_refs": [{"source_id": "demo_src_A", "message_id": "demo_src_A:msg_2", "quote": "从建设成果、推广等角度，把下面素材整理成一份官方汇报"}]},
    {"fact_id": "R002", "fact_type": "explicit_requirement", "claim": "600字以内（成稿字数口径需说明）",
     "value": None, "unit": None, "subject": None, "qualifiers": None,
     "explicit_user": True, "must_keep": False,
     "evidence_refs": [{"source_id": "demo_src_A", "message_id": "demo_src_A:msg_3", "quote": "600字以内"}]},
]

N1_TEXT = ("蓝星云课堂平台建设成果汇报：平台历经一年研发，试点覆盖12个班级。"
           "实测显示，教师备课时间平均每周节省约5小时，教学效率提升30%。"
           "推广方面，平台已在云星市40所学校上线，累计服务师生2万人。"
           "后续将围绕建设成果与推广经验持续扩大试点范围。")

N1_DECLARED = [
    {"fact_id": "F001", "value": "12", "unit": "个班级", "subject": "蓝星云课堂平台试点覆盖"},
    {"fact_id": "F002", "value": "5", "unit": "小时", "subject": "教师备课时间每周节省(实测口径)"},
    {"fact_id": "F003", "value": "30", "unit": "%", "subject": "教学效率提升(实测口径)"},
    {"fact_id": "F004", "value": "40", "unit": "所", "subject": "云星市上线学校"},
    {"fact_id": "F005", "value": "2", "unit": "万人", "subject": "累计服务师生"},
]

N1_FACT_REFS = [
    {"fact_id": "F001", "as_type": "achieved_fact"},
    {"fact_id": "F002", "as_type": "achieved_fact"},
    {"fact_id": "F003", "as_type": "achieved_fact"},
    {"fact_id": "F004", "as_type": "achieved_fact"},
    {"fact_id": "F005", "as_type": "achieved_fact"},
    {"fact_id": "R001", "as_type": "requirement"},
    {"fact_id": "R002", "as_type": "requirement"},
]


def ledger(facts, extra=None):
    obj = {
        "schema": "wrd-fact-ledger-v1",
        "ledger_id": "demo_ledger",
        "_note": "测试虚构样本，非真实业务来源",
        "facts": facts,
        "derived_rules": [
            {"rule_id": "DR1", "description": "官方汇报按角度归并，保留全部核心数字",
             "basis": "derived_policy_not_explicit_user"},
        ],
    }
    if extra:
        obj.update(extra)
    return obj


def draft(text, fact_refs=None, declared=None, kind="official_report", word_target=None,
          word_delivery=None, extra=None):
    obj = {
        "schema": "wrd-draft-v1",
        "draft_id": "demo_draft",
        "document_kind": kind,
        "text": text,
        "fact_refs": fact_refs if fact_refs is not None else N1_FACT_REFS,
        "declared_numbers": declared if declared is not None else N1_DECLARED,
        "word_delivery": word_delivery or {"target_provided": False, "written": False,
                                            "note": "未提供目标Word，仅交付文本"},
    }
    if word_target is not None:
        obj["word_target"] = word_target
    if extra:
        obj.update(extra)
    return obj


def write(name, obj):
    with open(os.path.join(FIX, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    write("sources_demo.json", SOURCES)

    # ---------- 正常 N1：官方汇报 ----------
    write("n1_ledger.json", ledger(N1_FACTS))
    write("n1_draft.json", draft(N1_TEXT, word_target={"char_limit": 600, "counting_mode": "non_whitespace"}))

    # ---------- 边界 B1a：字数恰好600（去空白口径） ----------
    filler = "试点班教师反馈良好，平台功能持续迭代完善。"
    t = N1_TEXT
    while count_chars(t, "non_whitespace") < 600:
        t += filler
    if count_chars(t, "non_whitespace") > 600:
        # 从末尾逐字符回退（filler 无数字，不会破坏已声明数值），保持恰好600
        while count_chars(t, "non_whitespace") > 600:
            t = t[:-1]
    assert count_chars(t, "non_whitespace") == 600, count_chars(t, "non_whitespace")
    b1a = draft(t, word_target={"char_limit": 600, "counting_mode": "non_whitespace"})
    b1a["draft_id"] = "b1a_exact_limit"
    write("b1a_draft.json", b1a)

    # ---------- 边界 B1b：恰好601（超1） ----------
    t2 = t + "超"
    assert count_chars(t2, "non_whitespace") == 601
    b1b = draft(t2, word_target={"char_limit": 600, "counting_mode": "non_whitespace"})
    b1b["draft_id"] = "b1b_over_by_one"
    write("b1b_draft.json", b1b)

    # ---------- 边界 B2a：省略非必保细节（F005），数字不改错 ----------
    b2a_text = ("蓝星云课堂平台建设成果汇报：平台历经一年研发，试点覆盖12个班级。"
                "实测显示，教师备课时间平均每周节省约5小时，教学效率提升30%。"
                "推广方面，平台已在云星市40所学校上线。"
                "后续将围绕建设成果与推广经验持续扩大试点范围。")
    b2a = draft(b2a_text,
                fact_refs=[r for r in N1_FACT_REFS if r["fact_id"] != "F005"],
                declared=[d for d in N1_DECLARED if d["fact_id"] != "F005"],
                word_target={"char_limit": 600, "counting_mode": "non_whitespace"})
    b2a["draft_id"] = "b2a_omit_optional"
    write("b2a_draft.json", b2a)

    # ---------- 边界 B2b：必保数字被改错（F002 must_keep，声明6≠5） ----------
    n1_ledger_must = ledger([dict(f) for f in N1_FACTS])
    for f in n1_ledger_must["facts"]:
        if f["fact_id"] == "F002":
            f["must_keep"] = True
    write("b2b_ledger.json", n1_ledger_must)
    b2b = draft(N1_TEXT, word_target={"char_limit": 600, "counting_mode": "non_whitespace"})
    b2b["declared_numbers"] = [dict(d) for d in N1_DECLARED]
    for d in b2b["declared_numbers"]:
        if d["fact_id"] == "F002":
            d["value"] = "6"
    b2b["draft_id"] = "b2b_wrong_number"
    write("b2b_draft.json", b2b)

    # ---------- 边界 B3a：未提供目标Word，显式 TEXT_ONLY ----------
    b3a = draft(N1_TEXT, word_target={"char_limit": 600, "counting_mode": "non_whitespace"},
                word_delivery={"target_provided": False, "written": False,
                               "note": "未提供目标Word，仅交付文本，未写入Word"})
    b3a["draft_id"] = "b3a_text_only"
    write("b3a_draft.json", b3a)

    # ---------- 错误 E6：缺必需证据（user_statement 无 evidence_refs） ----------
    e6_facts = [dict(f) for f in N1_FACTS]
    e6_facts[0] = dict(e6_facts[0])
    e6_facts[0]["evidence_refs"] = []
    write("e6_ledger.json", ledger(e6_facts))

    # ---------- 正常 N2：一段话成稿（规划目标口径） ----------
    n2_facts = [
        {"fact_id": "G001", "fact_type": "planned_goal", "claim": "预计五年到款总目标500万元",
         "value": "500", "unit": "万元", "subject": "五年到款总目标(预计)", "qualifiers": "预计/目标",
         "explicit_user": True, "must_keep": True,
         "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_1", "quote": "预计五年总目标500万元"}]},
        {"fact_id": "G002a", "fact_type": "planned_goal", "claim": "2027年完成首批试点校签约（计划）",
         "value": None, "unit": None, "subject": "首批试点校签约(计划)", "time": "2027年", "qualifiers": "计划",
         "explicit_user": True, "must_keep": False,
         "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_1", "quote": "2027年完成首批试点校签约"}]},
        {"fact_id": "G002b", "fact_type": "planned_goal", "claim": "2028年覆盖100所学校（计划）",
         "value": "100", "unit": "所学校", "subject": "覆盖学校(计划)", "time": "2028年", "qualifiers": "计划",
         "explicit_user": True, "must_keep": False,
         "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_1", "quote": "2028年覆盖100所学校"}]},
        {"fact_id": "G003a", "fact_type": "planned_goal", "claim": "底线目标300万元",
         "value": "300", "unit": "万元", "subject": "底线目标(预计)", "qualifiers": "目标",
         "explicit_user": True, "must_keep": False,
         "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_1", "quote": "底线目标300万"}]},
        {"fact_id": "G003b", "fact_type": "planned_goal", "claim": "挑战目标500万元",
         "value": "500", "unit": "万元", "subject": "挑战目标(预计)", "qualifiers": "目标",
         "explicit_user": True, "must_keep": False,
         "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_1", "quote": "挑战目标500万"}]},
        {"fact_id": "G003c", "fact_type": "planned_goal", "claim": "激进目标700万元",
         "value": "700", "unit": "万元", "subject": "激进目标(预计)", "qualifiers": "目标",
         "explicit_user": True, "must_keep": False,
         "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_1", "quote": "激进目标700万"}]},
        {"fact_id": "N001", "fact_type": "user_statement", "claim": "合作单位包括北辰研究院、南江实验学校",
         "value": None, "unit": None, "subject": None, "qualifiers": None,
         "explicit_user": True, "must_keep": False,
         "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_1", "quote": "合作单位包括北辰研究院、南江实验学校"}],
         # 嵌套 evidence_refs（正常）：模拟 A06 场景 task_switches
         "task_switches": [
             {"switch_id": "s1", "from_intent": "规划素材整编", "to_intent": "一段话成稿",
              "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_2", "quote": "整理成一段话"}]},
         ]},
        {"fact_id": "R101", "fact_type": "explicit_requirement", "claim": "整理成一段话，目标口径保持预计",
         "value": None, "unit": None, "subject": None, "qualifiers": None,
         "explicit_user": True, "must_keep": False,
         "evidence_refs": [{"source_id": "demo_src_B", "message_id": "demo_src_B:msg_2", "quote": "整理成一段话"}]},
    ]
    write("n2_ledger.json", ledger(n2_facts))
    n2_text = ("蓝星教育合作与到款规划：预计五年到款总目标500万元，底线目标300万元、挑战目标500万元、激进目标700万元；"
               "2027年完成首批试点校签约，2028年覆盖100所学校；合作单位包括北辰研究院、南江实验学校。")
    n2_refs = [
        {"fact_id": "G001", "as_type": "planned_goal"},
        {"fact_id": "G002a", "as_type": "planned_goal"},
        {"fact_id": "G002b", "as_type": "planned_goal"},
        {"fact_id": "G003a", "as_type": "planned_goal"},
        {"fact_id": "G003b", "as_type": "planned_goal"},
        {"fact_id": "G003c", "as_type": "planned_goal"},
        {"fact_id": "N001", "as_type": "context"},
        {"fact_id": "R101", "as_type": "requirement"},
    ]
    n2_declared = [
        {"fact_id": "G001", "value": "500", "unit": "万元", "subject": "五年到款总目标(预计)"},
        {"fact_id": "G002b", "value": "100", "unit": "所学校", "subject": "覆盖学校(计划)"},
        {"fact_id": "G003a", "value": "300", "unit": "万元", "subject": "底线目标(预计)"},
        {"fact_id": "G003b", "value": "500", "unit": "万元", "subject": "挑战目标(预计)"},
        {"fact_id": "G003c", "value": "700", "unit": "万元", "subject": "激进目标(预计)"},
    ]
    n2_draft = draft(n2_text, fact_refs=n2_refs, declared=n2_declared, kind="one_paragraph")
    n2_draft["draft_id"] = "n2_one_paragraph"
    write("n2_draft.json", n2_draft)

    # ---------- 错误 E3：嵌套 task_switches 中引文不是连续原文 ----------
    e3_facts = json.loads(json.dumps(n2_facts, ensure_ascii=False))
    for f in e3_facts:
        if f["fact_id"] == "N001":
            f["task_switches"][0]["evidence_refs"][0]["quote"] = "整理成三段话"
    write("e3_ledger.json", ledger(e3_facts))

    # ---------- 错误 E5：planned_goal 声明成 achieved_fact ----------
    e5 = draft(n2_text, fact_refs=n2_refs, declared=n2_declared, kind="one_paragraph")
    for r in e5["fact_refs"]:
        if r["fact_id"] == "G001":
            r["as_type"] = "achieved_fact"
    e5["draft_id"] = "e5_goal_as_achieved"
    write("e5_draft.json", e5)

    # ---------- 错误 E1：unknown fact ID ----------
    e1 = draft(N1_TEXT, word_target={"char_limit": 600, "counting_mode": "non_whitespace"})
    e1["fact_refs"] = [dict(r) for r in N1_FACT_REFS] + [{"fact_id": "F999", "as_type": "achieved_fact"}]
    e1["draft_id"] = "e1_unknown_fact"
    write("e1_draft.json", e1)

    # ---------- 错误 E2：quote 不是连续原文子串 ----------
    e2_facts = [dict(f) for f in N1_FACTS]
    e2_facts[1] = dict(e2_facts[1])
    e2_facts[1]["evidence_refs"] = [dict(e2_facts[1]["evidence_refs"][0])]
    e2_facts[1]["evidence_refs"][0]["quote"] = "教师备课时间平均每周节省5小时"  # 原文为「节省约5小时」
    write("e2_ledger.json", ledger(e2_facts))

    # ---------- 错误 E4a：声明单位与账本不符 ----------
    e4a = draft(N1_TEXT, word_target={"char_limit": 600, "counting_mode": "non_whitespace"})
    e4a["declared_numbers"] = [dict(d) for d in N1_DECLARED]
    for d in e4a["declared_numbers"]:
        if d["fact_id"] == "F002":
            d["unit"] = "天"
    e4a["draft_id"] = "e4a_unit_mismatch"
    write("e4a_draft.json", e4a)

    # ---------- 错误 E4b：声明主体与账本不符 ----------
    e4b = draft(N1_TEXT, word_target={"char_limit": 600, "counting_mode": "non_whitespace"})
    e4b["declared_numbers"] = [dict(d) for d in N1_DECLARED]
    for d in e4b["declared_numbers"]:
        if d["fact_id"] == "F002":
            d["subject"] = "行政事务耗时"
    e4b["draft_id"] = "e4b_subject_mismatch"
    write("e4b_draft.json", e4b)

    # ---------- 语义边界 E7：文本混入未声明数字90（程序不可判定，须 NEEDS_SEMANTIC_REVIEW） ----------
    e7 = draft(N1_TEXT + "平台内容准确率提升90%。",
               word_target={"char_limit": 600, "counting_mode": "non_whitespace"})
    e7["draft_id"] = "e7_undeclared_number"
    write("e7_draft.json", e7)

    # ---------- classify 请求 ----------
    write("c1_request.json", {"deliverable_kind": "official_report", "materials_present": True, "scope_clear": True})
    write("c2_request.json", {"deliverable_kind": "question_only_material", "materials_present": True, "scope_clear": False})
    write("c3_request.json", {"deliverable_kind": "official_report", "materials_present": False, "scope_clear": True})
    write("c4_request.json", {"deliverable_kind": "one_paragraph", "materials_present": True, "scope_clear": True})
    write("c5_request.json", {"deliverable_kind": "unclear_other", "materials_present": False, "scope_clear": False})

    print("fixtures written to", FIX)


if __name__ == "__main__":
    main()
