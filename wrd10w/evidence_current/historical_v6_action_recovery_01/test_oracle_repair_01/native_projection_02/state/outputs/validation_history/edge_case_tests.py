#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选技能边界开发测试（data_field_mask_request_v1）。

每次真实生成测试工作簿、真实调用 outputs/candidate/scripts/run.py、
真实重开输出断言结果；stdout/stderr 逐例保存到本目录 run_<case>.log。
退出码非0表示存在失败用例（失败日志保留，不删除）。
"""
import json
import os
import subprocess
import sys
from copy import copy
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
DATA = HERE / "testdata"
RUNNER = HERE.parent / "candidate" / "scripts" / "run.py"
DATA.mkdir(exist_ok=True)

results = []


def build_edge_workbook(path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "数据"
    ws.append(["序号", "客户名称", "联系人", "备注"])
    rows = [
        [1, "宁德时代新能源科技", "张三", "普通备注(联系人:测试)"],
        [2, "", "李", "x"],
        [3, None, "王测试姓名", "y"],
        [4, "=B2", "赵测试", "z"],
        [5, 12345, "钱测试", "w"],
        [6, True, "孙测试", "v"],
        [7, "美的", "美", "u"],
    ]
    for r in rows:
        ws.append(r)
    # 样式/布局要素
    c = ws["B2"]
    c.font = openpyxl.styles.Font(bold=True, color="FF0000")
    c.fill = openpyxl.styles.PatternFill("solid", fgColor="FFFF00")
    c.alignment = openpyxl.styles.Alignment(horizontal="center", wrap_text=True)
    ws.column_dimensions["B"].width = 33.5
    ws.freeze_panes = "A2"
    ws.merge_cells("A10:B10")
    wb.save(path)


def write_request(path: Path, req):
    path.write_text(json.dumps(req, ensure_ascii=False, indent=2), encoding="utf-8")


def run_case(case, req, out_root=None, expect_exit=0):
    req_path = DATA / f"req_{case}.json"
    write_request(req_path, req)
    cmd = [sys.executable, str(RUNNER), "--request", str(req_path)]
    if out_root:
        cmd += ["--output-root", str(out_root)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(HERE))
    (HERE / f"run_{case}.log").write_text(
        f"cmd: {' '.join(cmd)}\nexit: {r.returncode}\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}",
        encoding="utf-8")
    ok = r.returncode == expect_exit
    detail = ""
    if not ok:
        detail = f"exit={r.returncode} (期望{expect_exit}) stderr={r.stderr[:300]}"
    results.append((case, ok, detail))
    return r


def check(case, cond, detail=""):
    results.append((case, bool(cond), "" if cond else detail))


# ---------- 用例1：短文本/空值/公式/非文本/样式布局 ----------
wb_path = DATA / "edge_basic.xlsx"
build_edge_workbook(wb_path)
out1 = DATA / "edge_basic_out.xlsx"
req1 = {
    "schema_version": "data_field_mask_request_v1",
    "input_workbook": str(wb_path),
    "output_workbook": str(out1),
    "report_file": str(DATA / "edge_basic_report.json"),
    "worksheets": [{"name": "数据", "header_row": 1, "data_start_row": 2, "data_end_row": 9,
                    "columns": ["客户名称", "联系人"]}],
    "masking": {"prefix_chars": 2, "suffix_chars": 2, "replacement": "***"},
}
r = run_case("edge_basic", req1)
try:
    rep = json.loads((DATA / "edge_basic_report.json").read_text(encoding="utf-8"))
    t = rep["totals"]
    check("edge_basic_counts",
          (t["selected_cells"], t["changed_cells"], t["unchanged_text_cells"],
           t["blank_cells"], t["non_text_cells"], t["formula_cells"]) == (16, 2, 7, 4, 2, 1),
          f"totals={t}")
    wo = openpyxl.load_workbook(out1)
    ws = wo["数据"]
    check("edge_basic_masked", ws["B2"].value == "宁德***科技" and ws["C4"].value == "王测***姓名",
          f"B2={ws['B2'].value!r} C4={ws['C4'].value!r}")
    check("edge_basic_short_kept", ws["C2"].value == "张三" and ws["B8"].value == "美的",
          f"C2={ws['C2'].value!r} B8={ws['B8'].value!r}")
    check("edge_basic_blank_kept", ws["B3"].value in ("", None) and ws["B4"].value is None,
          f"B3={ws['B3'].value!r} B4={ws['B4'].value!r}")
    check("edge_basic_formula_kept", ws["B5"].value == "=B2" and ws["B5"].data_type == "f",
          f"B5={ws['B5'].value!r} type={ws['B5'].data_type}")
    check("edge_basic_nontext_kept", ws["B6"].value == 12345 and ws["B7"].value is True,
          f"B6={ws['B6'].value!r} B7={ws['B7'].value!r}")
    check("edge_basic_bracket_intact", ws["D2"].value == "普通备注(联系人:测试)",
          f"D2={ws['D2'].value!r}")
    wi = openpyxl.load_workbook(wb_path)
    a, b = wi["数据"], ws
    style_ok = all(copy(getattr(a["B2"], k)) == copy(getattr(b["B2"], k))
                   for k in ["font", "fill", "border", "alignment", "number_format"])
    check("edge_basic_style", style_ok and a["B2"].font.bold and str(a["B2"].fill.fgColor.rgb) == "00FFFF00" or style_ok,
          "B2样式不一致")
    check("edge_basic_layout",
          str(a.merged_cells.ranges) == str(b.merged_cells.ranges)
          and a.freeze_panes == b.freeze_panes
          and a.column_dimensions["B"].width == b.column_dimensions["B"].width,
          f"merged={b.merged_cells.ranges} freeze={b.freeze_panes} width={b.column_dimensions['B'].width}")
    check("edge_basic_non_target_sheet", wi.sheetnames == wo.sheetnames,
          f"sheets={wo.sheetnames}")
except Exception as exc:  # noqa: BLE001
    check("edge_basic_exception", False, repr(exc))

# ---------- 用例2：列换位（同表头不同物理列位） ----------
wb2 = openpyxl.Workbook()
ws2 = wb2.active
ws2.title = "S"
ws2.append(["联系电话", "应收金额", "客户名称", "联系人"])
ws2.append(["TEST-P-1", 100, " 北京某某科技有限公司 ", "张测试"])
ws2.append(["TEST-P-2", 200, "上海某某厂", "李"])
p2 = DATA / "edge_transposed.xlsx"
wb2.save(p2)
out2 = DATA / "edge_transposed_out.xlsx"
req2 = {
    "schema_version": "data_field_mask_request_v1",
    "input_workbook": str(p2), "output_workbook": str(out2),
    "report_file": str(DATA / "edge_transposed_report.json"),
    "worksheets": [{"name": "S", "header_row": 1, "data_start_row": 2, "data_end_row": 3,
                    "columns": ["客户名称", "联系电话"]}],
    "masking": {"prefix_chars": 2, "suffix_chars": 2, "replacement": "***"},
}
run_case("edge_transposed", req2)
wo2 = openpyxl.load_workbook(out2)["S"]
check("edge_transposed_masked",
      wo2["C2"].value == " 北京***公司 " and wo2["A2"].value == "TE***-1",
      f"C2={wo2['C2'].value!r} A2={wo2['A2'].value!r}")
check("edge_transposed_nontarget",
      wo2["B2"].value == 100 and wo2["D2"].value == "张测试" and wo2["C3"].value == "上海某某厂",
      f"B2={wo2['B2'].value!r} D2={wo2['D2'].value!r} C3={wo2['C3'].value!r}")

# ---------- 用例3：suffix_chars=0 且自定义replacement ----------
wb3 = openpyxl.Workbook()
ws3 = wb3.active
ws3.title = "S"
ws3.append(["客户名称"])
ws3.append(["宁德时代"])
p3 = DATA / "edge_suffix0.xlsx"
wb3.save(p3)
req3 = {
    "schema_version": "data_field_mask_request_v1",
    "input_workbook": str(p3), "output_workbook": str(DATA / "edge_suffix0_out.xlsx"),
    "report_file": str(DATA / "edge_suffix0_report.json"),
    "worksheets": [{"name": "S", "header_row": 1, "data_start_row": 2, "data_end_row": 2,
                    "columns": ["客户名称"]}],
    "masking": {"prefix_chars": 1, "suffix_chars": 0, "replacement": "@@"},
}
run_case("edge_suffix0", req3)
check("edge_suffix0_masked",
      openpyxl.load_workbook(DATA / "edge_suffix0_out.xlsx")["S"]["A2"].value == "宁@@",
      f"A2={openpyxl.load_workbook(DATA / 'edge_suffix0_out.xlsx')['S']['A2'].value!r}")

# ---------- 用例4：不同字符串同掩码 → 不加后缀（R07） ----------
wb4 = openpyxl.Workbook()
ws4 = wb4.active
ws4.title = "S"
ws4.append(["客户名称"])
ws4.append(["浙江一甲公司"])
ws4.append(["浙江二甲公司"])
p4 = DATA / "edge_collision.xlsx"
wb4.save(p4)
req4 = {
    "schema_version": "data_field_mask_request_v1",
    "input_workbook": str(p4), "output_workbook": str(DATA / "edge_collision_out.xlsx"),
    "report_file": str(DATA / "edge_collision_report.json"),
    "worksheets": [{"name": "S", "header_row": 1, "data_start_row": 2, "data_end_row": 3,
                    "columns": ["客户名称"]}],
    "masking": {"prefix_chars": 2, "suffix_chars": 2, "replacement": "***"},
}
run_case("edge_collision", req4)
ws4o = openpyxl.load_workbook(DATA / "edge_collision_out.xlsx")["S"]
check("edge_collision_no_suffix",
      ws4o["A2"].value == "浙江***公司" and ws4o["A2"].value == ws4o["A3"].value,
      f"A2={ws4o['A2'].value!r} A3={ws4o['A3'].value!r}")

# ---------- 用例5：默认输出路径（无--output-root，相对request目录） ----------
reqdir = DATA / "reqdir"
reqdir.mkdir(exist_ok=True)
wb5 = openpyxl.Workbook()
ws5 = wb5.active
ws5.title = "S"
ws5.append(["客户名称"])
ws5.append(["测试客户名称有限公司"])
(wb5.save(reqdir / "in.xlsx"))
req5 = {
    "schema_version": "data_field_mask_request_v1",
    "input_workbook": "in.xlsx", "output_workbook": "sub/out.xlsx",
    "report_file": "sub/report.json",
    "worksheets": [{"name": "S", "header_row": 1, "data_start_row": 2, "data_end_row": 2,
                    "columns": ["客户名称"]}],
    "masking": {"prefix_chars": 2, "suffix_chars": 2, "replacement": "***"},
}
write_request(reqdir / "request.json", req5)
cmd = [sys.executable, str(RUNNER), "--request", str(reqdir / "request.json")]
r5 = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(HERE))
(HERE / "run_default_path.log").write_text(
    f"cmd: {' '.join(cmd)}\nexit: {r5.returncode}\n{r5.stdout}\n{r5.stderr}", encoding="utf-8")
check("default_path",
      r5.returncode == 0 and (reqdir / "sub" / "out.xlsx").exists(),
      f"exit={r5.returncode} exists={(reqdir / 'sub' / 'out.xlsx').exists()}")

# ---------- 用例6-10：错误输入显式报错（R11） ----------
base_err = {
    "schema_version": "data_field_mask_request_v1",
    "input_workbook": str(p4), "output_workbook": str(DATA / "err_out.xlsx"),
    "report_file": str(DATA / "err_report.json"),
    "worksheets": [{"name": "S", "header_row": 1, "data_start_row": 2, "data_end_row": 3,
                    "columns": ["客户名称"]}],
    "masking": {"prefix_chars": 2, "suffix_chars": 2, "replacement": "***"},
}
# 6 重复表头
wb6 = openpyxl.Workbook()
ws6 = wb6.active
ws6.title = "S"
ws6.append(["客户名称", "客户名称"])
ws6.append(["甲甲甲甲甲", "乙乙乙乙乙"])
p6 = DATA / "err_dup_header.xlsx"
wb6.save(p6)
r6 = run_case("err_dup_header", {**base_err, "input_workbook": str(p6)}, expect_exit=2)
check("err_dup_header_msg", "不唯一" in r6.stderr, r6.stderr[:200])
# 7 缺表头
r7 = run_case("err_missing_header", {**base_err, "worksheets": [{"name": "S", "header_row": 1, "data_start_row": 2, "data_end_row": 2, "columns": ["不存在的列"]}]}, expect_exit=2)
check("err_missing_header_msg", "未找到表头" in r7.stderr, r7.stderr[:200])
# 8 缺sheet
r8 = run_case("err_missing_sheet", {**base_err, "worksheets": [{"name": "不存在", "header_row": 1, "data_start_row": 2, "data_end_row": 2, "columns": ["客户名称"]}]}, expect_exit=2)
check("err_missing_sheet_msg", "未找到工作表" in r8.stderr, r8.stderr[:200])
# 9 输出覆盖输入
r9 = run_case("err_output_over_input", {**base_err, "output_workbook": str(p4), "report_file": str(DATA / "err9_report.json")}, expect_exit=2)
check("err_output_over_input_msg", "不得覆盖输入" in r9.stderr, r9.stderr[:200])
# 10 行区间倒置 + 错误schema_version
r10 = run_case("err_bad_range", {**base_err, "worksheets": [{"name": "S", "header_row": 2, "data_start_row": 2, "data_end_row": 2, "columns": ["客户名称"]}]}, expect_exit=2)
r10b = run_case("err_bad_schema", {**base_err, "schema_version": "other_v1"}, expect_exit=2)
check("err_bad_range_msg", "行区间无效" in r10.stderr, r10.stderr[:200])
check("err_bad_schema_msg", "schema_version" in r10b.stderr, r10b.stderr[:200])

# ---------- 汇总 ----------
failed = [(c, d) for c, ok, d in results if not ok]
print(f"共 {len(results)} 项检查，失败 {len(failed)} 项")
for c, ok, d in results:
    print(f"  [{'PASS' if ok else 'FAIL'}] {c}" + (f" — {d}" if d else ""))
sys.exit(1 if failed else 0)
