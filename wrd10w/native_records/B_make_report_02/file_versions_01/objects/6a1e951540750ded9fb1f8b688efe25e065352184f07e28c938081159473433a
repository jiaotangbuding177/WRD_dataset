#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_pack.py — 通用事实账本成稿技能的结构校验器（公开CLI）。

用法：
  python validate_pack.py validate --ledger LEDGER.json [--sources SOURCES.json] --draft DRAFT.json --report REPORT.json
  python validate_pack.py classify --request REQUEST.json [--report REPORT.json]

退出码（validate）：0=结构校验通过；1=结构校验失败；2=输入/用法错误。
退出码（classify）：0=已产出用途门控决策（decision见report）；2=输入/用法错误。

范围声明（诚实边界）：本工具只做确定性结构/类型/数字/长度检查。
成稿文字与事实之间的语义忠实度、外部真实性，程序无法可靠判定，
一律列入 needs_semantic_review（NEEDS_SEMANTIC_REVIEW），绝不输出"语义已通过"的结论。
"""

import argparse
import json
import os
import re
import sys

FACT_TYPES = {"user_statement", "planned_goal", "explicit_requirement", "new_assumption"}
DOC_KINDS = {"official_report", "one_paragraph"}
AS_TYPES = {"achieved_fact", "planned_goal", "context", "requirement"}
COUNT_MODES = {"all_characters", "non_whitespace"}
DEFAULT_PARA_MAX = {"official_report": 8, "one_paragraph": 1}
# 账本 fact_type 允许的成稿陈述角色（planned_goal 不得声明为 achieved_fact）
TYPE_TO_AS = {
    "user_statement": {"achieved_fact", "context"},
    "planned_goal": {"planned_goal"},
    "explicit_requirement": {"requirement"},
    "new_assumption": {"context"},
}


class InputError(Exception):
    pass


def norm(s):
    if isinstance(s, str):
        return re.sub(r"\s+", "", s)
    return s


def count_chars(text, mode):
    """字数口径：all_characters=全部字符；non_whitespace=去除空白后的字符数。"""
    if mode == "all_characters":
        return len(text)
    return sum(1 for c in text if not c.isspace())


def load_json(path, what):
    if not os.path.isfile(path):
        raise InputError("missing %s file: %s" % (what, path))
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        raise InputError("cannot parse %s JSON (%s): %s" % (what, path, e))


def iter_evidence_refs(node, path="$"):
    """递归遍历 JSON 树，产出 (path, ref)。

    任何键名恰为 evidence_refs 的列表，其每个 dict 元素都被独立校验。
    这保证嵌套结构（如 task_switches 等自定义字段）内的引用不会漏检。
    """
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "evidence_refs" and isinstance(v, list):
                for i, ref in enumerate(v):
                    if isinstance(ref, dict):
                        yield "%s.evidence_refs[%d]" % (path, i), ref
            else:
                yield from iter_evidence_refs(v, path + "." + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from iter_evidence_refs(v, "%s[%d]" % (path, i))


def add_sources(container, index):
    if not isinstance(container, dict):
        return
    srcs = container.get("sources")
    if not isinstance(srcs, list):
        return
    for s in srcs:
        if not isinstance(s, dict):
            continue
        sid = s.get("source_id")
        if not sid:
            continue
        entry = index.setdefault(sid, {})
        msgs = s.get("messages")
        if isinstance(msgs, list):
            for m in msgs:
                if isinstance(m, dict) and m.get("message_id"):
                    entry[m["message_id"]] = m.get("content") or ""
        elif isinstance(msgs, dict):
            for mid, content in msgs.items():
                entry[mid] = content or ""


def run_validate(args):
    failures = []
    checks_passed = []
    reviews = []
    notes = []
    report = {
        "tool": "validate_pack.py",
        "mode": "validate",
        "verdict": None,
        "structural_pass": False,
        "failures": failures,
        "checks_passed": checks_passed,
        "needs_semantic_review": reviews,
        "notes": notes,
        "meta": {},
    }

    def fail(cid, detail, path=None):
        item = {"id": cid, "detail": detail}
        if path:
            item["path"] = path
        failures.append(item)

    def review(cid, detail):
        reviews.append({"id": "NEEDS_SEMANTIC_REVIEW:" + cid, "detail": detail})

    def input_error(msg):
        report["verdict"] = "INPUT_ERROR"
        report["failures"].append({"id": "input_error", "detail": msg})
        finish(report, args, exit_code=2)
        return 2

    try:
        ledger = load_json(args.ledger, "ledger")
        draft = load_json(args.draft, "draft")
        src_obj = load_json(args.sources, "sources") if args.sources else None
    except InputError as e:
        return input_error(str(e))

    if not isinstance(ledger, dict) or not isinstance(draft, dict):
        return input_error("ledger and draft must be JSON objects")

    # ---------- 源索引（--sources 与账本内嵌 sources 均可） ----------
    index = {}
    add_sources(src_obj, index)
    add_sources(ledger, index)
    if not index:
        notes.append("NO_SOURCE_TEXTS_INDEXED: 未提供任何源消息文本，evidence_refs 的原文连续性无法校验")

    # ---------- 1) 账本基础结构 ----------
    facts = ledger.get("facts")
    fact_map = {}
    ok = True
    if not isinstance(facts, list) or not facts:
        fail("ledger_basics", "facts 必须是非空列表")
        ok = False
        facts = []
    for i, f in enumerate(facts):
        if not isinstance(f, dict):
            fail("ledger_basics", "facts[%d] 必须是对象" % i, "$.facts[%d]" % i)
            ok = False
            continue
        fid = f.get("fact_id")
        if not isinstance(fid, str) or not fid:
            fail("ledger_basics", "facts[%d] 缺少 fact_id" % i, "$.facts[%d]" % i)
            ok = False
            continue
        if fid in fact_map:
            fail("ledger_basics", "fact_id 重复: %s" % fid, "$.facts[%d]" % i)
            ok = False
            continue
        fact_map[fid] = f
        ftype = f.get("fact_type")
        if ftype not in FACT_TYPES:
            fail("ledger_basics", "fact %s 的 fact_type 非法: %r" % (fid, ftype), "$.facts[%d]" % i)
            ok = False
        refs = f.get("evidence_refs")
        if not isinstance(refs, list):
            fail("ledger_basics", "fact %s 缺少 evidence_refs 列表" % fid, "$.facts[%d]" % i)
            ok = False
            refs = []
            f["evidence_refs"] = refs
        if ftype in ("user_statement", "planned_goal", "explicit_requirement") and not refs:
            fail("missing_required_evidence",
                 "fact %s（%s）缺少必需证据 evidence_refs 为空" % (fid, ftype),
                 "$.facts[%d].evidence_refs" % i)
            ok = False
        if f.get("must_keep") and ftype == "new_assumption":
            fail("ledger_basics", "fact %s 是 new_assumption，不得标记 must_keep=true" % fid,
                 "$.facts[%d]" % i)
            ok = False
    rules = ledger.get("derived_rules", [])
    if isinstance(rules, list):
        for i, r in enumerate(rules):
            if not isinstance(r, dict) or r.get("basis") != "derived_policy_not_explicit_user":
                fail("ledger_basics",
                     "derived_rules[%d] 必须声明 basis=derived_policy_not_explicit_user（派生策略不得冒充用户明确要求）" % i,
                     "$.derived_rules[%d]" % i)
                ok = False
    if ok:
        checks_passed.append("ledger_basics")

    # ---------- 2) 成稿基础结构 ----------
    ok = True
    kind = draft.get("document_kind")
    if kind not in DOC_KINDS:
        fail("draft_basics", "document_kind 非法: %r（允许 %s）" % (kind, sorted(DOC_KINDS)))
        ok = False
    text = draft.get("text")
    if not isinstance(text, str) or not text.strip():
        fail("draft_basics", "text 必须是非空字符串")
        ok = False
        text = ""
    fact_refs = draft.get("fact_refs")
    if not isinstance(fact_refs, list) or not fact_refs:
        fail("draft_basics", "fact_refs 必须是非空列表")
        ok = False
        fact_refs = []
    for i, r in enumerate(fact_refs):
        if not isinstance(r, dict) or not isinstance(r.get("fact_id"), str):
            fail("draft_basics", "fact_refs[%d] 必须是含 fact_id 的对象" % i, "$.fact_refs[%d]" % i)
            ok = False
        elif r.get("as_type") not in AS_TYPES:
            fail("draft_basics", "fact_refs[%d] 的 as_type 非法: %r" % (i, r.get("as_type")),
                 "$.fact_refs[%d]" % i)
            ok = False
    if ok:
        checks_passed.append("draft_basics")

    # ---------- 3) 递归校验全部 evidence_refs（账本+成稿，含任意嵌套） ----------
    ok = True
    for root_name, root in (("ledger", ledger), ("draft", draft)):
        for path, ref in iter_evidence_refs(root):
            sid = ref.get("source_id")
            mid = ref.get("message_id")
            quote = ref.get("quote")
            if not (isinstance(sid, str) and sid and isinstance(mid, str) and mid):
                fail("evidence_ref_invalid", "缺少 source_id 或 message_id", "%s:%s" % (root_name, path))
                ok = False
                continue
            if sid not in index:
                fail("evidence_unknown_source", "未知 source_id: %s" % sid, "%s:%s" % (root_name, path))
                ok = False
                continue
            if mid not in index[sid]:
                fail("evidence_unknown_message", "source %s 下未知 message_id: %s" % (sid, mid),
                     "%s:%s" % (root_name, path))
                ok = False
                continue
            if not isinstance(quote, str) or not quote.strip():
                fail("evidence_ref_invalid", "quote 必须是非空字符串", "%s:%s" % (root_name, path))
                ok = False
                continue
            if quote not in index[sid][mid]:
                fail("evidence_quote_not_contiguous",
                     "quote 不是源消息的连续原文子串: source=%s message=%s quote=%r" % (sid, mid, quote),
                     "%s:%s" % (root_name, path))
                ok = False
    if ok and index:
        checks_passed.append("evidence_refs")

    # ---------- 4) fact ID 闭合（成稿引用必须存在；必保/要求事实必须被引用） ----------
    ok = True
    used_ids = set()
    for i, r in enumerate(fact_refs):
        fid = r.get("fact_id")
        if not isinstance(fid, str):
            continue
        used_ids.add(fid)
        if fid not in fact_map:
            fail("unknown_fact_reference", "成稿引用了账本中不存在的 fact_id: %s" % fid,
                 "$.fact_refs[%d]" % i)
            ok = False
    omitted_optional = []
    for fid, f in fact_map.items():
        if f.get("must_keep") and fid not in used_ids:
            fail("missing_must_keep_fact", "必保事实 %s（must_keep=true）未被成稿引用" % fid)
            ok = False
        if f.get("fact_type") == "explicit_requirement" and fid not in used_ids:
            fail("missing_requirement_fact", "用户明确要求 %s（explicit_requirement）未被成稿引用" % fid)
            ok = False
        if fid not in used_ids and not f.get("must_keep"):
            omitted_optional.append(fid)
    if omitted_optional:
        notes.append("OMITTED_NON_MUST_KEEP_FACTS: 非必保事实未被成稿引用: %s" % ",".join(omitted_optional))
    if ok:
        checks_passed.append("fact_closure")

    # ---------- 5) 类型规则：planned_goal 不得被声明成已实现事实 ----------
    ok = True
    for i, r in enumerate(fact_refs):
        fid = r.get("fact_id")
        f = fact_map.get(fid)
        if not f:
            continue
        as_t = r.get("as_type")
        allowed = TYPE_TO_AS.get(f.get("fact_type"))
        if allowed is not None and as_t not in allowed:
            if f.get("fact_type") == "planned_goal" and as_t == "achieved_fact":
                fail("type_mismatch_planned_goal_as_achieved",
                     "规划目标 %s 被声明为已实现事实（as_type=achieved_fact）；目标口径必须保持" % fid,
                     "$.fact_refs[%d]" % i)
            else:
                fail("type_mismatch",
                     "fact %s（%s）不允许 as_type=%s（允许 %s）" % (fid, f.get("fact_type"), as_t, sorted(allowed)),
                     "$.fact_refs[%d]" % i)
            ok = False
    if ok:
        checks_passed.append("type_rules")

    # ---------- 6) 声明数字/单位/主体 与账本一致，且确实出现在成稿文本 ----------
    ok = True
    stripped_text = norm(text)
    declared = draft.get("declared_numbers", [])
    if not isinstance(declared, list):
        declared = []
        fail("declared_numbers", "declared_numbers 必须是列表")
        ok = False
    covered_values = set()
    for i, d in enumerate(declared):
        if not isinstance(d, dict):
            fail("declared_numbers", "declared_numbers[%d] 必须是对象" % i, "$.declared_numbers[%d]" % i)
            ok = False
            continue
        fid = d.get("fact_id")
        f = fact_map.get(fid)
        if f is None:
            fail("declared_number_unknown_fact", "declared_numbers[%d] 引用未知 fact_id: %s" % (i, fid),
                 "$.declared_numbers[%d]" % i)
            ok = False
            continue
        dval = d.get("value")
        fval = f.get("value")
        if norm(str(dval)) != norm(str(fval)):
            fail("declared_number_value_mismatch",
                 "fact %s 数值不符：账本 value=%r，成稿声明 value=%r" % (fid, fval, dval),
                 "$.declared_numbers[%d]" % i)
            ok = False
        funit = f.get("unit")
        dunit = d.get("unit")
        if funit is not None and dunit is not None and norm(str(funit)) != norm(str(dunit)):
            fail("declared_number_unit_mismatch",
                 "fact %s 单位不符：账本 unit=%r，成稿声明 unit=%r" % (fid, funit, dunit),
                 "$.declared_numbers[%d]" % i)
            ok = False
        fsubj = f.get("subject")
        dsubj = d.get("subject")
        if fsubj and dsubj and norm(str(fsubj)) != norm(str(dsubj)):
            fail("declared_number_subject_mismatch",
                 "fact %s 主体关联不符：账本 subject=%r，成稿声明 subject=%r" % (fid, fsubj, dsubj),
                 "$.declared_numbers[%d]" % i)
            ok = False
        if funit is not None and dunit is None:
            review("DECLARED_UNIT_MISSING", "declared_numbers[%d]（fact %s）未声明单位，账本 unit=%r" % (i, fid, funit))
        if fsubj and dsubj is None:
            review("DECLARED_SUBJECT_MISSING", "declared_numbers[%d]（fact %s）未声明主体，账本 subject=%r" % (i, fid, fsubj))
        if isinstance(dval, str) and dval:
            covered_values.add(norm(dval))
            if norm(dval) not in stripped_text:
                fail("declared_number_absent_from_text",
                     "声明数值 %r（fact %s）未出现在成稿文本中" % (dval, fid),
                     "$.declared_numbers[%d]" % i)
                ok = False
    # 文本中未被声明覆盖的数字 → 语义复核（可能是合法改写，也可能是数字改错；程序无法判定）
    tokens = sorted(set(re.findall(r"\d+(?:\.\d+)?", text)))
    uncovered = [t for t in tokens if t not in covered_values]
    if uncovered:
        review("UNDECLARED_NUMBERS",
               "成稿文本中出现未在 declared_numbers 声明的数字: %s；需人工语义复核是否与账本一致" % ",".join(uncovered))
    if ok:
        checks_passed.append("declared_numbers")

    # ---------- 7) 字数约束 ----------
    ok = True
    wt = draft.get("word_target")
    if wt is not None:
        if not isinstance(wt, dict) or not isinstance(wt.get("char_limit"), int) or wt["char_limit"] <= 0:
            fail("length", "word_target 必须是含正整数 char_limit 的对象")
            ok = False
        else:
            mode = wt.get("counting_mode", "non_whitespace")
            if mode not in COUNT_MODES:
                fail("length", "counting_mode 非法: %r（允许 %s）" % (mode, sorted(COUNT_MODES)))
                ok = False
            else:
                if "counting_mode" not in wt:
                    notes.append("COUNTING_MODE_DEFAULTED: 未声明 counting_mode，默认采用 non_whitespace（去空白字符计数）")
                n = count_chars(text, mode)
                limit = wt["char_limit"]
                if n > limit:
                    fail("length_over_limit", "字数超限：口径=%s 实际=%d 上限=%d（超 %d）" % (mode, n, limit, n - limit))
                    ok = False
                else:
                    notes.append("LENGTH_OK: 口径=%s 实际=%d 上限=%d" % (mode, n, limit))
                    if n == limit:
                        notes.append("LENGTH_EXACTLY_AT_LIMIT: 字数恰好等于阈值（边界通过）")
    if ok:
        checks_passed.append("length")

    # ---------- 8) 段落约束 ----------
    ok = True
    pc = draft.get("paragraph_constraints") or {}
    pmax = pc.get("max", DEFAULT_PARA_MAX.get(kind, 8))
    pmin = pc.get("min", 1)
    paras = [p for p in re.split(r"\n+", text) if p.strip()]
    if pmax is not None and len(paras) > pmax:
        fail("paragraph_count_over_max", "段落数 %d 超过上限 %d" % (len(paras), pmax))
        ok = False
    elif len(paras) < pmin:
        fail("paragraph_count_below_min", "段落数 %d 低于下限 %d" % (len(paras), pmin))
        ok = False
    if ok:
        checks_passed.append("paragraphs")

    # ---------- 9) 事实类型冲突（同主体+数值+单位但类型不同） ----------
    ok = True
    seen = {}
    for fid, f in fact_map.items():
        if f.get("value") is None:
            continue
        key = (norm(str(f.get("subject") or "")), norm(str(f.get("value"))), norm(str(f.get("unit") or "")))
        seen.setdefault(key, []).append((fid, f.get("fact_type")))
    for key, entries in seen.items():
        types = {t for _, t in entries}
        if len(types) > 1:
            fail("fact_type_conflict",
                 "同一主体/数值/单位存在冲突类型声明: %s -> %s" % (entries, sorted(types)))
            ok = False
    if ok:
        checks_passed.append("conflicts")

    # ---------- 10) Word 交付状态 ----------
    ok = True
    wd = draft.get("word_delivery") or {}
    target_provided = bool(wd.get("target_provided", False))
    written = bool(wd.get("written", False))
    if written and not target_provided:
        fail("word_delivery_inconsistent", "written=true 但 target_provided=false，状态矛盾")
        ok = False
    if not target_provided:
        notes.append("TEXT_ONLY_NO_WORD_TARGET: 未提供目标Word，本次仅交付文本，未写入Word")
    if written:
        review("WORD_WRITE_UNVERIFIED", "成稿声明已写入Word；本工具无法验证文件内容，交付前需人工/渲染核验")
    if ok:
        checks_passed.append("word_delivery")

    # ---------- 11) 常设语义复核项（诚实边界，永不输出"语义已通过"） ----------
    done_ids = set()
    for r in fact_refs:
        fid = r.get("fact_id")
        f = fact_map.get(fid)
        if not f or fid in done_ids:
            continue
        done_ids.add(fid)
        as_t = r.get("as_type")
        if as_t == "achieved_fact" and f.get("fact_type") == "user_statement":
            review("USER_CLAIM_UNVERIFIED",
                   "fact %s 为用户提供陈述，外部真实性未经独立核实；成稿按已实现口径表述需人工复核措辞与归因" % fid)
        if as_t == "planned_goal":
            review("GOAL_WORDING_CHECK",
                   "fact %s 为规划目标；成稿须保持目标/预计口径（未完成语义），需人工复核措辞" % fid)
        if f.get("fact_type") == "new_assumption":
            review("ASSUMPTION_MARKING", "fact %s 为新假设；成稿中必须明确标注为假设，需人工复核" % fid)
    if not index:
        review("NO_SOURCE_TEXTS", "未提供源文本索引，全部引文核验被跳过；结果不构成引用校验通过")

    report["structural_pass"] = not failures
    if failures:
        report["verdict"] = "STRUCTURAL_FAIL"
    elif reviews:
        report["verdict"] = "STRUCTURAL_PASS_SEMANTIC_REVIEW_PENDING"
    else:
        report["verdict"] = "STRUCTURAL_PASS"
    report["meta"]["external_verification"] = "none：所有 user_provided 事实均未做外部独立核实"
    report["meta"]["scope"] = "仅结构/类型/数字/长度/引用连续性的确定性检查；语义忠实度需独立人工复核"
    return finish(report, args, exit_code=0 if not failures else 1)


def run_classify(args):
    report = {
        "tool": "validate_pack.py",
        "mode": "classify",
        "verdict": "CLASSIFY_DONE",
        "decision": None,
        "reasons": [],
        "meta": {"scope": "用途门控决策，不构成质量批准；决策依据仅来自请求声明的字段"},
    }
    try:
        req = load_json(args.request, "request")
    except InputError as e:
        report["verdict"] = "INPUT_ERROR"
        report["reasons"].append(str(e))
        return finish(report, args, exit_code=2)
    kind = req.get("deliverable_kind")
    materials = bool(req.get("materials_present"))
    scope_clear = bool(req.get("scope_clear"))
    if not materials:
        decision = "NEEDS_EVIDENCE"
        report["reasons"].append("素材缺失或未提供：不因缺输入判定 NO_VALUE，标 NEEDS_EVIDENCE 待补齐素材/规则后重评")
    elif kind == "official_report":
        if scope_clear:
            decision = "PROCEED_OFFICIAL_REPORT"
            report["reasons"].append("目标为官方汇报成稿且范围明确：可进入账本→成稿→校验流程")
        else:
            decision = "NEEDS_EVIDENCE"
            report["reasons"].append("范围不明确：标 NEEDS_EVIDENCE，待用户澄清后再成稿")
    elif kind == "one_paragraph":
        if scope_clear:
            decision = "PROCEED_ONE_PARAGRAPH"
            report["reasons"].append("目标为一段话成稿且范围明确：可进入账本→成稿→校验流程")
        else:
            decision = "NEEDS_EVIDENCE"
            report["reasons"].append("范围不明确：标 NEEDS_EVIDENCE，待用户澄清后再成稿")
    elif kind in ("question_only_material", "unclear_other"):
        decision = "OUT_OF_SCOPE_DEFER"
        report["reasons"].append(
            "只出题/仅需求描述或范围不明：不盲合为官方汇报成稿机制；标 DEFER 待明确范围，非 NO_VALUE")
    else:
        decision = "NEEDS_EVIDENCE"
        report["reasons"].append("deliverable_kind 未知: %r；标 NEEDS_EVIDENCE 待澄清" % (kind,))
    report["decision"] = decision
    return finish(report, args, exit_code=0)


def finish(report, args, exit_code):
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    print("VERDICT: %s" % report["verdict"])
    if report.get("decision"):
        print("DECISION: %s" % report["decision"])
    print("FAILURES: %d" % len(report.get("failures", [])))
    for it in report.get("failures", []):
        print("FAIL %s: %s%s" % (it["id"], it["detail"], (" [%s]" % it["path"]) if it.get("path") else ""))
    n_rev = len(report.get("needs_semantic_review", []))
    if n_rev:
        print("NEEDS_SEMANTIC_REVIEW: %d item(s)" % n_rev)
        for it in report["needs_semantic_review"]:
            print("REVIEW %s: %s" % (it["id"], it["detail"]))
    for n in report.get("notes", []):
        print("NOTE %s" % n)
    return exit_code


def main(argv=None):
    ap = argparse.ArgumentParser(description="通用事实账本成稿技能校验器（仅结构检查，语义需独立复核）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="校验 账本+成稿")
    pv.add_argument("--ledger", required=True, help="事实账本 JSON 路径")
    pv.add_argument("--draft", required=True, help="成稿 JSON 路径")
    pv.add_argument("--sources", help="源消息文本 JSON 路径（也可内嵌于账本 sources 字段）")
    pv.add_argument("--report", help="结构化报告输出路径")

    pc = sub.add_parser("classify", help="请求用途门控（官方汇报/一段话/只出题/不明）")
    pc.add_argument("--request", required=True, help="请求声明 JSON 路径")
    pc.add_argument("--report", help="结构化报告输出路径")

    args = ap.parse_args(argv)
    if args.cmd == "validate":
        return run_validate(args)
    return run_classify(args)


if __name__ == "__main__":
    sys.exit(main())
