#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_tests.py — 通过技能公开CLI执行正常/边界/错误fixture测试，逐项断言并记录全过程。

记录内容：每次实际命令、输入/产物SHA256、实际退出码/verdict、逐项断言与失败原因。
断言是精确的：预期拒绝必须出现对应失败ID；边界必须按口径区分；不是"退出非0就算过"。
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
REPORTS = os.path.join(HERE, "reports")
SKILL_CLI = os.path.join(HERE, "..", "skill", "scripts", "validate_pack.py")
LOG_PATH = os.path.join(HERE, "test_run_log.json")

os.makedirs(REPORTS, exist_ok=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_case(name, ledger, draft_path, sources, expects):
    report = os.path.join(REPORTS, name + "_report.json")
    cmd = [sys.executable, SKILL_CLI, "validate",
           "--ledger", ledger, "--draft", draft_path, "--sources", sources, "--report", report]
    return {"name": name, "type": "validate", "cmd": cmd, "report": report,
            "inputs": [p for p in (ledger, draft_path, sources)], "expects": expects}


def classify_case(name, request, expects):
    report = os.path.join(REPORTS, name + "_report.json")
    cmd = [sys.executable, SKILL_CLI, "classify", "--request", request, "--report", report]
    return {"name": name, "type": "classify", "cmd": cmd, "report": report,
            "inputs": [request], "expects": expects}


def build_cases():
    S = os.path.join(FIX, "sources_demo.json")
    cases = []

    # ---------- 正常 ----------
    cases.append(validate_case("N1_normal_official_report",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "n1_draft.json"), S,
                               {"exit": 0, "verdict": "STRUCTURAL_PASS_SEMANTIC_REVIEW_PENDING",
                                "no_failures": True, "review_contains": ["NEEDS_SEMANTIC_REVIEW:USER_CLAIM_UNVERIFIED"]}))
    cases.append(validate_case("N2_normal_one_paragraph_nested_ok",
                               os.path.join(FIX, "n2_ledger.json"), os.path.join(FIX, "n2_draft.json"), S,
                               {"exit": 0, "verdict": "STRUCTURAL_PASS_SEMANTIC_REVIEW_PENDING",
                                "no_failures": True, "review_contains": ["NEEDS_SEMANTIC_REVIEW:GOAL_WORDING_CHECK"]}))

    # ---------- 边界 ----------
    cases.append(validate_case("B1a_length_exactly_at_limit",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "b1a_draft.json"), S,
                               {"exit": 0, "no_failures": True, "notes_contains": ["LENGTH_EXACTLY_AT_LIMIT"]}))
    cases.append(validate_case("B1b_length_over_by_one",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "b1b_draft.json"), S,
                               {"exit": 1, "fail_present": ["length_over_limit"]}))
    cases.append(validate_case("B2a_omit_optional_detail_numbers_ok",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "b2a_draft.json"), S,
                               {"exit": 0, "no_failures": True,
                                "notes_contains": ["OMITTED_NON_MUST_KEEP_FACTS", "F005"]}))
    cases.append(validate_case("B2b_must_keep_number_altered",
                               os.path.join(FIX, "b2b_ledger.json"), os.path.join(FIX, "b2b_draft.json"), S,
                               {"exit": 1, "fail_present": ["declared_number_value_mismatch"]}))
    cases.append(validate_case("B3a_no_word_target_text_only",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "b3a_draft.json"), S,
                               {"exit": 0, "no_failures": True, "notes_contains": ["TEXT_ONLY_NO_WORD_TARGET"]}))
    cases.append(classify_case("C1_classify_official_report_ok",
                               os.path.join(FIX, "c1_request.json"),
                               {"exit": 0, "decision": "PROCEED_OFFICIAL_REPORT"}))
    cases.append(classify_case("C2_classify_question_only_defer",
                               os.path.join(FIX, "c2_request.json"),
                               {"exit": 0, "decision": "OUT_OF_SCOPE_DEFER"}))
    cases.append(classify_case("C3_classify_no_materials_needs_evidence",
                               os.path.join(FIX, "c3_request.json"),
                               {"exit": 0, "decision": "NEEDS_EVIDENCE"}))
    cases.append(classify_case("C4_classify_one_paragraph_ok",
                               os.path.join(FIX, "c4_request.json"),
                               {"exit": 0, "decision": "PROCEED_ONE_PARAGRAPH"}))
    cases.append(classify_case("C5_classify_unclear_needs_evidence_not_no_value",
                               os.path.join(FIX, "c5_request.json"),
                               {"exit": 0, "decision": "NEEDS_EVIDENCE"}))

    # ---------- 错误 ----------
    cases.append(validate_case("E1_unknown_fact_id",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "e1_draft.json"), S,
                               {"exit": 1, "fail_present": ["unknown_fact_reference"]}))
    cases.append(validate_case("E2_quote_not_contiguous",
                               os.path.join(FIX, "e2_ledger.json"), os.path.join(FIX, "n1_draft.json"), S,
                               {"exit": 1, "fail_present": ["evidence_quote_not_contiguous"]}))
    cases.append(validate_case("E3_nested_task_switches_bad_quote",
                               os.path.join(FIX, "e3_ledger.json"), os.path.join(FIX, "n2_draft.json"), S,
                               {"exit": 1, "fail_present": ["evidence_quote_not_contiguous"],
                                "fail_path_contains": ["task_switches"]}))
    cases.append(validate_case("E4a_declared_unit_mismatch",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "e4a_draft.json"), S,
                               {"exit": 1, "fail_present": ["declared_number_unit_mismatch"]}))
    cases.append(validate_case("E4b_declared_subject_mismatch",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "e4b_draft.json"), S,
                               {"exit": 1, "fail_present": ["declared_number_subject_mismatch"]}))
    cases.append(validate_case("E5_planned_goal_as_achieved",
                               os.path.join(FIX, "n2_ledger.json"), os.path.join(FIX, "e5_draft.json"), S,
                               {"exit": 1, "fail_present": ["type_mismatch_planned_goal_as_achieved"]}))
    cases.append(validate_case("E6_missing_required_evidence",
                               os.path.join(FIX, "e6_ledger.json"), os.path.join(FIX, "n1_draft.json"), S,
                               {"exit": 1, "fail_present": ["missing_required_evidence"]}))
    cases.append(validate_case("E7_undeclared_number_needs_semantic_review",
                               os.path.join(FIX, "n1_ledger.json"), os.path.join(FIX, "e7_draft.json"), S,
                               {"exit": 0, "verdict": "STRUCTURAL_PASS_SEMANTIC_REVIEW_PENDING",
                                "no_failures": True, "review_contains": ["UNDECLARED_NUMBERS", "90"]}))
    cases.append(validate_case("E8_missing_ledger_file_input_error",
                               os.path.join(FIX, "nonexistent_ledger.json"), os.path.join(FIX, "n1_draft.json"), S,
                               {"exit": 2, "verdict": "INPUT_ERROR"}))
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
    if "decision" in exp:
        check("decision==%s" % exp["decision"], (report_obj or {}).get("decision") == exp["decision"])
    if exp.get("no_failures"):
        check("failures==[]", (report_obj or {}).get("failures") == [])
    for fid in exp.get("fail_present", []):
        check("fail_present:%s" % fid,
              any(f.get("id") == fid for f in (report_obj or {}).get("failures", [])))
    for sub in exp.get("fail_path_contains", []):
        check("fail_path_contains:%s" % sub,
              any(sub in (f.get("path", "") + f.get("detail", "")) for f in (report_obj or {}).get("failures", [])))
    for sub in exp.get("notes_contains", []):
        check("notes_contains:%s" % sub,
              any(sub in n for n in (report_obj or {}).get("notes", [])))
    for sub in exp.get("review_contains", []):
        check("review_contains:%s" % sub,
              any(sub in (it.get("id", "") + it.get("detail", "")) for it in (report_obj or {}).get("needs_semantic_review", [])))
    return ok


def main():
    # 0) 重新生成夹具（可复现）
    gen = subprocess.run([sys.executable, os.path.join(HERE, "make_fixtures.py")],
                         capture_output=True, text=True)
    if gen.returncode != 0:
        print("FIXTURE GENERATION FAILED:", gen.stderr)
        return 2

    log = {"schema": "wrd-b-test-run-log-v1",
           "runner": "run_tests.py",
           "cli_under_test": os.path.abspath(SKILL_CLI),
           "cli_sha256": sha256(SKILL_CLI),
           "note": "全部夹具素材为虚构测试样本，非真实业务来源；断言精确到失败ID/决策值/边界标记，非仅退出码",
           "cases": []}

    n_pass = n_fail = 0
    for case in build_cases():
        entry = {"name": case["name"], "command": " ".join(case["cmd"]),
                 "input_sha256": {p: sha256(p) for p in case["inputs"] if os.path.isfile(p)}}
        proc = subprocess.run(case["cmd"], capture_output=True, text=True)
        entry["exit_code"] = proc.returncode
        entry["stdout_tail"] = "\n".join(proc.stdout.strip().splitlines()[:20])
        report_obj = None
        if os.path.isfile(case["report"]):
            with open(case["report"], "r", encoding="utf-8") as f:
                report_obj = json.load(f)
            entry["report_sha256"] = sha256(case["report"])
            entry["report_path"] = os.path.relpath(case["report"], HERE)
        assertions = []
        passed = evaluate(case, proc.returncode, report_obj, assertions)
        entry["assertions"] = assertions
        entry["case_result"] = "PASS" if passed else "FAIL"
        if not passed:
            entry["failure_reason"] = [a["desc"] for a in assertions if not a["passed"]]
            n_fail += 1
        else:
            n_pass += 1
        log["cases"].append(entry)

    log["summary"] = {"total": len(log["cases"]), "passed": n_pass, "failed": n_fail,
                       "interpretation_limit": "测试通过仅证明这些局部结构检查有效，不构成语义正确或技能质量/复用收益的批准"}
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print("TEST SUMMARY: total=%d passed=%d failed=%d" % (len(log["cases"]), n_pass, n_fail))
    for c in log["cases"]:
        if c["case_result"] == "FAIL":
            print("FAILED CASE: %s -> %s" % (c["name"], c.get("failure_reason")))
    print("LOG:", LOG_PATH)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
