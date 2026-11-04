#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_tests_extra.py — 局部修订补充测试：通过技能公开CLI精确断言正反例。

与原 run_tests.py 相同原则：断言精确到失败ID/路径/决策值/复核项，不是"退出非0就算过"。
不修改原21测试的任何预期；本文件只补充 feedback 要求的真实正反例。
日志：extra_test_log.json（含命令、输入/报告SHA、退出码、逐项断言）。
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures_extra")
REPORTS = os.path.join(HERE, "reports_extra")
SKILL_CLI = os.path.join(HERE, "..", "skill", "scripts", "validate_pack.py")
LOG_PATH = os.path.join(HERE, "extra_test_log.json")

os.makedirs(REPORTS, exist_ok=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def case(name, ledger, draft_path, sources, expects):
    report = os.path.join(REPORTS, name + "_report.json")
    cmd = [sys.executable, SKILL_CLI, "validate",
           "--ledger", ledger, "--draft", draft_path, "--sources", sources, "--report", report]
    return {"name": name, "cmd": cmd, "report": report,
            "inputs": [p for p in (ledger, draft_path, sources)], "expects": expects}


def build_cases():
    S = os.path.join(FIX, "sources_extra.json")
    fx = lambda n: os.path.join(FIX, n)  # noqa: E731
    cases = []

    # 正例：跨年 actual/goal 同值合法（不得再有 fact_type_conflict；不确定性进语义复核）
    cases.append(case("X1_different_years_actual_goal_same_value_legal",
                      fx("x1_ledger.json"), fx("x1_draft.json"), S,
                      {"exit": 0, "verdict": "STRUCTURAL_PASS_SEMANTIC_REVIEW_PENDING",
                       "no_failures": True, "fail_absent": ["fact_type_conflict"],
                       "review_contains": ["FACT_TYPE_AMBIGUOUS"]}))
    # 正例：同一年 actual 完成值与 goal 目标同值合法共存
    cases.append(case("X2_same_year_actual_goal_same_value_coexist_legal",
                      fx("x2_ledger.json"), fx("x2_draft.json"), S,
                      {"exit": 0, "verdict": "STRUCTURAL_PASS_SEMANTIC_REVIEW_PENDING",
                       "no_failures": True, "fail_absent": ["fact_type_conflict"],
                       "review_contains": ["FACT_TYPE_AMBIGUOUS"]}))
    # 反例：planned_goal 引用为 achieved_fact 仍须硬拒（不得因冲突判定放宽而失效）
    cases.append(case("X3_planned_goal_as_achieved_still_rejected",
                      fx("x1_ledger.json"), fx("x3_draft.json"), S,
                      {"exit": 1, "fail_present": ["type_mismatch_planned_goal_as_achieved"]}))
    # 反例：嵌套 evidence_refs 非列表 -> 精确失败ID+路径
    cases.append(case("X4_nested_evidence_refs_not_list_rejected",
                      fx("x4_ledger.json"), fx("x4_draft.json"), S,
                      {"exit": 1, "fail_present": ["evidence_refs_not_list"],
                       "fail_path_contains": ["task_switches", "evidence_refs"],
                       "fail_count": 1}))
    # 反例：嵌套 evidence_refs 列表元素非对象 -> 精确失败ID+路径
    cases.append(case("X5_nested_evidence_refs_item_not_object_rejected",
                      fx("x5_ledger.json"), fx("x5_draft.json"), S,
                      {"exit": 1, "fail_present": ["evidence_refs_item_not_object"],
                       "fail_path_contains": ["task_switches", "evidence_refs[0]"],
                       "fail_count": 1}))
    # 反例：嵌套 evidence_refs 为对象（非列表）-> 拒绝
    cases.append(case("X6_nested_evidence_refs_dict_rejected",
                      fx("x6_ledger.json"), fx("x6_draft.json"), S,
                      {"exit": 1, "fail_present": ["evidence_refs_not_list"],
                       "fail_path_contains": ["task_switches"]}))
    # 正例：合法嵌套 quote 继续通过
    cases.append(case("X7_nested_valid_quote_still_passes",
                      fx("x7_ledger.json"), fx("x7_draft.json"), S,
                      {"exit": 0, "no_failures": True}))
    # 反例：嵌套错误 quote 继续拒绝
    cases.append(case("X8_nested_bad_quote_still_rejected",
                      fx("x8_ledger.json"), fx("x8_draft.json"), S,
                      {"exit": 1, "fail_present": ["evidence_quote_not_contiguous"],
                       "fail_path_contains": ["task_switches"]}))
    # 正例：空的可选引用列表合法（不等于必需事实缺证）
    cases.append(case("X9_empty_optional_refs_legal",
                      fx("x9_ledger.json"), fx("x9_draft.json"), S,
                      {"exit": 0, "no_failures": True, "fail_absent": ["missing_required_evidence"]}))
    # 反例：必需事实空引用列表仍拒绝
    cases.append(case("X10_required_fact_empty_refs_still_rejected",
                      fx("x10_ledger.json"), fx("x10_draft.json"), S,
                      {"exit": 1, "fail_present": ["missing_required_evidence"]}))
    # 反例：成稿侧嵌套畸形 evidence_refs（draft 根）-> 拒绝且路径含 draft
    cases.append(case("X11_draft_side_nested_malformed_rejected",
                      fx("x11_ledger.json"), fx("x11_draft.json"), S,
                      {"exit": 1, "fail_present": ["evidence_refs_not_list"],
                       "fail_path_contains": ["draft", "attachments"]}))
    # 反例：账本事实级 evidence_refs 非列表（顶层形状）-> 拒绝且含路径
    cases.append(case("X12_fact_level_refs_not_list_rejected",
                      fx("x12_ledger.json"), fx("x12_draft.json"), S,
                      {"exit": 1, "fail_present": ["ledger_basics"],
                       "fail_path_contains": ["$.facts[0].evidence_refs"]}))
    return cases


def evaluate(case, exit_code, report_obj, assertions):
    exp = case["expects"]
    ok = True

    def check(desc, cond):
        nonlocal ok
        assertions.append({"desc": desc, "passed": bool(cond)})
        if not cond:
            ok = False

    check("exit_code==%s" % exp.get("exit"), exit_code == exp.get("exit"))
    if "verdict" in exp:
        check("verdict==%s" % exp["verdict"], (report_obj or {}).get("verdict") == exp["verdict"])
    if exp.get("no_failures"):
        check("failures==[]", (report_obj or {}).get("failures") == [])
    if "fail_count" in exp:
        check("failures_count==%d" % exp["fail_count"],
              len((report_obj or {}).get("failures", [])) == exp["fail_count"])
    for fid in exp.get("fail_present", []):
        check("fail_present:%s" % fid,
              any(f.get("id") == fid for f in (report_obj or {}).get("failures", [])))
    for fid in exp.get("fail_absent", []):
        check("fail_absent:%s" % fid,
              not any(f.get("id") == fid for f in (report_obj or {}).get("failures", [])))
    for sub in exp.get("fail_path_contains", []):
        check("fail_path_contains:%s" % sub,
              any(sub in (f.get("path", "") + f.get("detail", "")) for f in (report_obj or {}).get("failures", [])))
    for sub in exp.get("review_contains", []):
        check("review_contains:%s" % sub,
              any(sub in (it.get("id", "") + it.get("detail", "")) for it in (report_obj or {}).get("needs_semantic_review", [])))
    return ok


def main():
    gen = subprocess.run([sys.executable, os.path.join(HERE, "make_fixtures_extra.py")],
                         capture_output=True, text=True)
    if gen.returncode != 0:
        print("EXTRA FIXTURE GENERATION FAILED:", gen.stderr)
        return 2

    log = {"schema": "wrd-revision-extra-test-log-v1",
           "runner": "run_tests_extra.py",
           "cli_under_test": os.path.abspath(SKILL_CLI),
           "cli_sha256": sha256(SKILL_CLI),
           "note": "补充正反例均为明确虚构样本；断言精确到失败ID/路径/复核项，非仅退出码",
           "cases": []}
    n_pass = n_fail = 0
    for c in build_cases():
        entry = {"name": c["name"], "command": " ".join(c["cmd"]),
                 "input_sha256": {p: sha256(p) for p in c["inputs"] if os.path.isfile(p)}}
        proc = subprocess.run(c["cmd"], capture_output=True, text=True)
        entry["exit_code"] = proc.returncode
        entry["stdout_tail"] = "\n".join(proc.stdout.strip().splitlines()[:20])
        report_obj = None
        if os.path.isfile(c["report"]):
            with open(c["report"], "r", encoding="utf-8") as f:
                report_obj = json.load(f)
            entry["report_sha256"] = sha256(c["report"])
        assertions = []
        passed = evaluate(c, proc.returncode, report_obj, assertions)
        entry["assertions"] = assertions
        entry["case_result"] = "PASS" if passed else "FAIL"
        if not passed:
            entry["failure_reason"] = [a["desc"] for a in assertions if not a["passed"]]
            n_fail += 1
        else:
            n_pass += 1
        log["cases"].append(entry)
    log["summary"] = {"total": len(log["cases"]), "passed": n_pass, "failed": n_fail,
                       "interpretation_limit": "补充测试通过仅证明局部修订后的结构检查有效，不构成语义正确或技能质量/复用收益的批准"}
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print("EXTRA TEST SUMMARY: total=%d passed=%d failed=%d" % (len(log["cases"]), n_pass, n_fail))
    for c in log["cases"]:
        if c["case_result"] == "FAIL":
            print("FAILED CASE: %s -> %s" % (c["name"], c.get("failure_reason")))
    print("LOG:", LOG_PATH)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
