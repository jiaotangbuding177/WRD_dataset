#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_fixtures_extra.py — 生成局部修订的补充正反例夹具（明确虚构，非真实业务来源）。

覆盖 actual_repair_feedback.json 要求的补充用例：
  X1  不同年份 actual/goal 同值 -> 合法（不再硬判 fact_type_conflict）
  X2  同一年 actual 完成值与 goal 目标同值 -> 合法共存
  X3  planned_goal 被引用为 achieved_fact -> 仍硬性拒绝
  X4  嵌套 evidence_refs 为字符串 -> 拒绝（evidence_refs_not_list，含路径）
  X5  嵌套 evidence_refs 列表元素非对象([42]同型) -> 拒绝（evidence_refs_item_not_object）
  X6  嵌套 evidence_refs 为对象({}) -> 拒绝（非列表形状）
  X7  合法嵌套 quote -> 继续通过
  X8  嵌套错误 quote -> 继续拒绝
  X9  空的可选引用列表（new_assumption / 嵌套）-> 合法，不等于必需事实缺证
  X10 必需事实空引用列表 -> 仍拒绝 missing_required_evidence
  X11 成稿侧嵌套畸形 evidence_refs -> 拒绝（draft 根）
  X12 账本事实级 evidence_refs 非列表 -> 拒绝（含路径）

年份/数值/主体均为通用样例（2024/2027/2030/2031、120人、80万元等），
校验器逻辑不含任何按具体年份/数值/主体/文件名的特判。
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures_extra")
os.makedirs(FIX, exist_ok=True)

SOURCES = {
    "schema": "wrd-sources-v1",
    "_note": "补充测试虚构样本，非真实业务来源，与 feedback 无真实企业对应",
    "sources": [
        {
            "source_id": "src_x",
            "messages": [
                {"message_id": "src_x:msg1", "role": "user",
                 "content": "2024年实际培训120人；2027年计划培训120人。"},
                {"message_id": "src_x:msg2", "role": "user",
                 "content": "2030年实际培训120人；2030年计划培训120人。"},
                {"message_id": "src_x:msg3", "role": "user",
                 "content": "2031年服务器运维支出80万元。"},
            ],
        }
    ],
}


def ref(mid, quote):
    return {"source_id": "src_x", "message_id": "src_x:" + mid, "quote": quote}


def ledger(facts, extra=None):
    obj = {
        "schema": "wrd-fact-ledger-v1",
        "ledger_id": "extra_ledger",
        "_note": "补充测试虚构样本，非真实业务来源",
        "facts": facts,
        "derived_rules": [],
    }
    if extra:
        obj.update(extra)
    return obj


def draft(text, fact_refs, declared, kind="one_paragraph", extra=None):
    obj = {
        "schema": "wrd-draft-v1",
        "draft_id": "extra_draft",
        "document_kind": kind,
        "text": text,
        "fact_refs": fact_refs,
        "declared_numbers": declared,
        "word_delivery": {"target_provided": False, "written": False},
    }
    if extra:
        obj.update(extra)
    return obj


def write(name, obj):
    with open(os.path.join(FIX, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    write("sources_extra.json", SOURCES)

    # ---------- X1：不同年份 actual/goal 同值，合法 ----------
    f1 = {"fact_id": "F1", "fact_type": "user_statement", "claim": "2024年实际培训120人",
          "value": "120", "unit": "人", "subject": "培训人数", "time": "2024",
          "explicit_user": True, "must_keep": True, "evidence_refs": [ref("msg1", "2024年实际培训120人")]}
    f2 = {"fact_id": "F2", "fact_type": "planned_goal", "claim": "2027年计划培训120人",
          "value": "120", "unit": "人", "subject": "培训人数", "time": "2027",
          "explicit_user": True, "must_keep": True, "evidence_refs": [ref("msg1", "2027年计划培训120人")]}
    write("x1_ledger.json", ledger([f1, f2]))
    write("x1_draft.json", draft("2024年实际培训120人，2027年计划培训120人。",
                                 [{"fact_id": "F1", "as_type": "achieved_fact"},
                                  {"fact_id": "F2", "as_type": "planned_goal"}],
                                 [{"fact_id": "F1", "value": "120", "unit": "人", "subject": "培训人数"},
                                  {"fact_id": "F2", "value": "120", "unit": "人", "subject": "培训人数"}]))

    # ---------- X2：同一年(2030) actual 完成值与 goal 目标同值，合法共存 ----------
    f3 = {"fact_id": "F3", "fact_type": "user_statement", "claim": "2030年实际培训120人",
          "value": "120", "unit": "人", "subject": "培训人数", "time": "2030",
          "explicit_user": True, "must_keep": True, "evidence_refs": [ref("msg2", "2030年实际培训120人")]}
    f4 = {"fact_id": "F4", "fact_type": "planned_goal", "claim": "2030年计划培训120人",
          "value": "120", "unit": "人", "subject": "培训人数", "time": "2030",
          "explicit_user": True, "must_keep": True, "evidence_refs": [ref("msg2", "2030年计划培训120人")]}
    write("x2_ledger.json", ledger([f3, f4]))
    write("x2_draft.json", draft("2030年实际培训120人，2030年计划培训120人。",
                                 [{"fact_id": "F3", "as_type": "achieved_fact"},
                                  {"fact_id": "F4", "as_type": "planned_goal"}],
                                 [{"fact_id": "F3", "value": "120", "unit": "人", "subject": "培训人数"},
                                  {"fact_id": "F4", "value": "120", "unit": "人", "subject": "培训人数"}]))

    # ---------- X3：planned_goal 引用为 achieved_fact，仍须拒（X1 账本） ----------
    x3 = draft("2024年实际培训120人，2027年计划培训120人。",
               [{"fact_id": "F1", "as_type": "achieved_fact"},
                {"fact_id": "F2", "as_type": "achieved_fact"}],
               [{"fact_id": "F1", "value": "120", "unit": "人", "subject": "培训人数"},
                {"fact_id": "F2", "value": "120", "unit": "人", "subject": "培训人数"}])
    x3["draft_id"] = "x3_goal_as_achieved"
    write("x3_draft.json", x3)

    # ---------- X4/X5/X6：嵌套 evidence_refs 形状畸形 ----------
    base_fact = {"fact_id": "F5", "fact_type": "user_statement", "claim": "2030年实际培训120人",
                 "value": "120", "unit": "人", "subject": "培训人数", "time": "2030",
                 "explicit_user": True, "must_keep": True, "evidence_refs": [ref("msg2", "2030年实际培训120人")]}
    single_draft = draft("2030年实际培训120人。",
                         [{"fact_id": "F5", "as_type": "achieved_fact"}],
                         [{"fact_id": "F5", "value": "120", "unit": "人", "subject": "培训人数"}])

    bad_str = json.loads(json.dumps(base_fact, ensure_ascii=False))
    bad_str["task_switches"] = [{"switch_id": "s1", "evidence_refs": "malformed-reference-string"}]
    write("x4_ledger.json", ledger([bad_str]))
    write("x4_draft.json", single_draft)

    bad_item = json.loads(json.dumps(base_fact, ensure_ascii=False))
    bad_item["task_switches"] = [{"switch_id": "s1", "evidence_refs": [42]}]
    write("x5_ledger.json", ledger([bad_item]))
    write("x5_draft.json", single_draft)

    bad_dict = json.loads(json.dumps(base_fact, ensure_ascii=False))
    bad_dict["task_switches"] = [{"switch_id": "s1", "evidence_refs": {"source_id": "src_x"}}]
    write("x6_ledger.json", ledger([bad_dict]))
    write("x6_draft.json", single_draft)

    # ---------- X7：合法嵌套 quote 继续通过 ----------
    good_nested = json.loads(json.dumps(base_fact, ensure_ascii=False))
    good_nested["task_switches"] = [
        {"switch_id": "s1", "from_intent": "素材整编", "to_intent": "一段话成稿",
         "evidence_refs": [ref("msg3", "2031年服务器运维支出80万元")]}]
    write("x7_ledger.json", ledger([good_nested]))
    write("x7_draft.json", single_draft)

    # ---------- X8：嵌套错误 quote 继续拒绝 ----------
    bad_quote = json.loads(json.dumps(good_nested, ensure_ascii=False))
    bad_quote["task_switches"][0]["evidence_refs"][0]["quote"] = "2031年运维支出80万元"
    write("x8_ledger.json", ledger([bad_quote]))
    write("x8_draft.json", single_draft)

    # ---------- X9：空的可选引用列表合法（new_assumption + 嵌套空列表） ----------
    a1 = {"fact_id": "A1", "fact_type": "new_assumption", "claim": "按内部估算口径测算（新假设）",
          "value": None, "unit": None, "subject": None,
          "explicit_user": False, "must_keep": False,
          "evidence_refs": [],
          "task_switches": [{"switch_id": "s1", "evidence_refs": []}]}
    write("x9_ledger.json", ledger([a1]))
    x9 = draft("按内部估算口径测算。", [{"fact_id": "A1", "as_type": "context"}], [])
    write("x9_draft.json", x9)

    # ---------- X10：必需事实空引用列表仍拒绝 ----------
    req_fact = json.loads(json.dumps(base_fact, ensure_ascii=False))
    req_fact["evidence_refs"] = []
    write("x10_ledger.json", ledger([req_fact]))
    write("x10_draft.json", single_draft)

    # ---------- X11：成稿侧嵌套畸形 evidence_refs（draft 根） ----------
    x11 = json.loads(json.dumps(single_draft, ensure_ascii=False))
    x11["attachments"] = [{"name": "note", "evidence_refs": "oops-not-a-list"}]
    x11["draft_id"] = "x11_draft_side_malformed"
    write("x11_draft.json", x11)
    write("x11_ledger.json", ledger([json.loads(json.dumps(base_fact, ensure_ascii=False))]))

    # ---------- X12：账本事实级 evidence_refs 非列表（顶层形状） ----------
    top_bad = json.loads(json.dumps(base_fact, ensure_ascii=False))
    top_bad["evidence_refs"] = "oops-not-a-list"
    write("x12_ledger.json", ledger([top_bad]))
    write("x12_draft.json", single_draft)

    print("extra fixtures written to", FIX)


if __name__ == "__main__":
    main()
