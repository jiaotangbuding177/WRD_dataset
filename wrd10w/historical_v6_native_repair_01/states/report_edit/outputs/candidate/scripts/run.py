#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Excel 指定字段文本脱敏（公开契约 data_field_mask_request_v1）。

用法:
    python run.py --request <request.json> [--output-root <dir>]

路径解析（契约附议 path_resolution_addendum_a1）:
    - input_workbook 的相对路径以 request.json 所在目录为基准；绝对路径保持绝对。
    - 未提供 --output-root 时，output_workbook / report_file 的相对路径同样以
      request.json 所在目录为基准；提供时，这两个相对路径改映射到该输出根下，
      绝对路径保持绝对。inputs 只读，任何情况下不写入。
    - 实际交付路径通过 stdout 摘要明确报告。

业务规则摘要（与契约 business_rules R01-R12 一致）:
    R02/R03 按工作表名+表头行精确匹配列名（要求唯一），只处理
            header_row < data_start_row <= data_end_row 的矩形交集。
    R04     普通非空字符串按 Unicode 码点计数，不 trim、不归一化、不删括号；
            长度 > prefix_chars + suffix_chars 时输出前缀+replacement+后缀。
    R05     长度 <= 前后保留之和、真空单元格与空字符串原样保留。
    R06     数值/布尔/公式/日期等非文本目标原样保留并分别计数。
    R07     相同字符串同参数得到相同结果，不添加任何撞名后缀。
    R08/R09 不改非目标值、类型、行列位置、表名与表顺序、样式、列宽行高、
            合并区域、冻结窗格。
    R10     报告不含任何原值或原值到脱敏值的映射。
    R11     结构性错误显式报错退出（exit 2），不交付半成品。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import copy
from pathlib import Path

import openpyxl

REQUEST_SCHEMA_VERSION = "data_field_mask_request_v1"
REPORT_SCHEMA_VERSION = "data_field_mask_report_v1"


class ContractError(Exception):
    """违反契约 R11 的输入错误：显式报错，不猜测目标。"""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_path(base: Path, p: str) -> Path:
    pp = Path(p)
    return pp if pp.is_absolute() else base / pp


def validate_request(req: dict) -> None:
    if not isinstance(req, dict):
        raise ContractError("request.json 顶层必须是JSON对象")
    for k in ("schema_version", "input_workbook", "output_workbook",
              "report_file", "worksheets", "masking"):
        if k not in req:
            raise ContractError(f"request.json 缺少必需字段: {k}")
    allowed_top = {"schema_version", "input_workbook", "output_workbook",
                   "report_file", "worksheets", "masking"}
    extra_top = set(req) - allowed_top
    if extra_top:
        raise ContractError(f"request.json 含多余字段: {sorted(extra_top)}（契约不允许额外属性）")
    if req["schema_version"] != REQUEST_SCHEMA_VERSION:
        raise ContractError(
            f"schema_version 必须为 {REQUEST_SCHEMA_VERSION}，实际: {req['schema_version']!r}")
    for k in ("input_workbook", "output_workbook", "report_file"):
        if not isinstance(req[k], str) or not req[k]:
            raise ContractError(f"{k} 必须是非空字符串")
    if not isinstance(req["worksheets"], list) or not req["worksheets"]:
        raise ContractError("worksheets 必须是非空数组")
    for i, ws in enumerate(req["worksheets"]):
        if not isinstance(ws, dict):
            raise ContractError(f"worksheets[{i}] 必须是对象")
        for k in ("name", "header_row", "data_start_row", "data_end_row", "columns"):
            if k not in ws:
                raise ContractError(f"worksheets[{i}] 缺少字段: {k}")
        ws_allowed = {"name", "header_row", "data_start_row", "data_end_row", "columns"}
        ws_extra = set(ws) - ws_allowed
        if ws_extra:
            raise ContractError(f"worksheets[{i}] 含多余字段: {sorted(ws_extra)}（契约不允许额外属性）")
        if not isinstance(ws["name"], str) or not ws["name"]:
            raise ContractError(f"worksheets[{i}].name 必须是非空字符串")
        for k in ("header_row", "data_start_row", "data_end_row"):
            v = ws[k]
            if not isinstance(v, int) or isinstance(v, bool):
                raise ContractError(f"worksheets[{i}].{k} 必须是整数")
        if ws["header_row"] < 1 or ws["data_start_row"] < 2 or ws["data_end_row"] < 2:
            raise ContractError(f"worksheets[{i}] 行号越界: header_row>=1, data_start_row>=2, data_end_row>=2")
        if not (ws["header_row"] < ws["data_start_row"] <= ws["data_end_row"]):
            raise ContractError(
                f"worksheets[{i}] 行区间无效: 必须满足 header_row < data_start_row <= data_end_row")
        cols = ws["columns"]
        if (not isinstance(cols, list) or not cols
                or any(not isinstance(c, str) or not c for c in cols)):
            raise ContractError(f"worksheets[{i}].columns 必须是非空字符串数组")
        if len(set(cols)) != len(cols):
            raise ContractError(f"worksheets[{i}].columns 存在重复表头名: {cols}")
    m = req["masking"]
    if not isinstance(m, dict):
        raise ContractError("masking 必须是对象")
    m_allowed = {"prefix_chars", "suffix_chars", "replacement"}
    m_extra = set(m) - m_allowed
    if m_extra:
        raise ContractError(f"masking 含多余字段: {sorted(m_extra)}（契约不允许额外属性）")
    for k in ("prefix_chars", "suffix_chars", "replacement"):
        if k not in m:
            raise ContractError(f"masking 缺少字段: {k}")
    for k in ("prefix_chars", "suffix_chars"):
        v = m[k]
        if not isinstance(v, int) or isinstance(v, bool) or not (0 <= v <= 8):
            raise ContractError(f"masking.{k} 必须是 0..8 的整数")
    rep = m["replacement"]
    if not isinstance(rep, str) or not (1 <= len(rep) <= 16):
        raise ContractError("masking.replacement 必须是长度 1..16 的字符串")


def mask_text(value: str, prefix_chars: int, suffix_chars: int, replacement: str) -> str:
    """R04/R05：Unicode 码点计数；长度不足等于保留之和时原样返回。"""
    if len(value) <= prefix_chars + suffix_chars:
        return value
    head = value[:prefix_chars]
    tail = value[-suffix_chars:] if suffix_chars > 0 else ""
    return head + replacement + tail


def classify(cell) -> str:
    """R06/报告口径：formula | blank | text | non_text。"""
    if cell.data_type == "f":
        return "formula"
    v = cell.value
    if v is None or (isinstance(v, str) and v == ""):
        return "blank"
    if isinstance(v, str):
        return "text"
    return "non_text"


def locate_columns(ws, spec) -> dict:
    """R02：按表头行完整值精确匹配，目标表头必须唯一。返回 {表头名: 列号}。"""
    header_values = []
    for cell in ws[spec["header_row"]]:
        header_values.append(cell.value if isinstance(cell.value, str) else None)
    mapping = {}
    for col_name in spec["columns"]:
        hits = [idx for idx, v in enumerate(header_values, start=1) if v == col_name]
        if not hits:
            raise ContractError(
                f"工作表 '{ws.title}' 第{spec['header_row']}行未找到表头 '{col_name}'（精确匹配）")
        if len(hits) > 1:
            raise ContractError(
                f"工作表 '{ws.title}' 第{spec['header_row']}行表头 '{col_name}' 不唯一（出现{len(hits)}次）")
        mapping[col_name] = hits[0]
    return mapping


def style_sig(cell):
    # cell.font 等返回 StyleProxy 包装对象，其 __eq__ 未委托给真实样式对象；
    # 用 copy() 解包得到真实样式对象后再比较，避免同值样式被误判不等。
    return (copy(cell.font), copy(cell.fill), copy(cell.border),
            copy(cell.alignment), cell.number_format)


def layout_sig(ws):
    cols = sorted(
        (key, getattr(d, "width", None), getattr(d, "hidden", None))
        for key, d in ws.column_dimensions.items()
    )
    rows = sorted(
        (key, getattr(d, "height", None), getattr(d, "hidden", None))
        for key, d in ws.row_dimensions.items()
    )
    return (ws.title, str(ws.merged_cells.ranges), ws.freeze_panes, cols, rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Excel指定字段文本脱敏 data_field_mask_request_v1")
    ap.add_argument("--request", required=True, help="请求JSON路径")
    ap.add_argument("--output-root", default=None, help="可选隔离输出根目录")
    args = ap.parse_args()

    request_path = Path(args.request)
    if not request_path.is_file():
        print(f"ERROR: 请求文件不存在: {request_path}", file=sys.stderr)
        return 2
    try:
        req = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: 请求文件不可读或非法JSON: {exc}", file=sys.stderr)
        return 2
    try:
        validate_request(req)
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    req_base = request_path.parent.resolve()
    in_path = resolve_path(req_base, req["input_workbook"]).resolve()
    out_base = Path(args.output_root).resolve() if args.output_root else req_base
    out_path = resolve_path(out_base, req["output_workbook"]).resolve()
    report_path = resolve_path(out_base, req["report_file"]).resolve()

    if in_path == out_path or in_path == report_path:
        print("ERROR: 输出/报告路径不得覆盖输入工作簿（R11）", file=sys.stderr)
        return 2
    if not in_path.is_file():
        print(f"ERROR: 输入工作簿不存在: {in_path}", file=sys.stderr)
        return 2

    input_sha_before = sha256_file(in_path)
    try:
        wb = openpyxl.load_workbook(in_path, data_only=False)
    except Exception as exc:  # noqa: BLE001 - 输入不可读按契约显式报错
        print(f"ERROR: 输入不是可读的xlsx工作簿: {exc}", file=sys.stderr)
        return 2

    m = req["masking"]
    prefix_chars, suffix_chars, replacement = m["prefix_chars"], m["suffix_chars"], m["replacement"]

    report_sheets = []
    totals = {"selected_cells": 0, "changed_cells": 0, "unchanged_text_cells": 0,
              "blank_cells": 0, "non_text_cells": 0, "formula_cells": 0}
    expected = []  # (sheet_title, coord, expected_value) 仅驻留内存，不写入任何交付物
    target_coords = set()  # (sheet_title, coord)

    try:
        for spec in req["worksheets"]:
            name = spec["name"]
            if name not in wb.sheetnames:
                raise ContractError(f"未找到工作表: {name!r}；现有: {wb.sheetnames}")
            ws = wb[name]
            col_map = locate_columns(ws, spec)
            counts = {"selected_cells": 0, "changed_cells": 0, "unchanged_text_cells": 0,
                      "blank_cells": 0, "non_text_cells": 0, "formula_cells": 0}
            for row in range(spec["data_start_row"], spec["data_end_row"] + 1):
                for col_name in spec["columns"]:
                    cell = ws.cell(row=row, column=col_map[col_name])
                    kind = classify(cell)
                    counts["selected_cells"] += 1
                    if kind == "text":
                        new_val = mask_text(cell.value, prefix_chars, suffix_chars, replacement)
                        if new_val != cell.value:
                            counts["changed_cells"] += 1
                            cell.value = new_val
                        else:
                            counts["unchanged_text_cells"] += 1
                        expected.append((name, cell.coordinate, new_val))
                    elif kind == "blank":
                        counts["blank_cells"] += 1
                        expected.append((name, cell.coordinate, cell.value))
                    elif kind == "formula":
                        counts["formula_cells"] += 1
                        expected.append((name, cell.coordinate, cell.value))
                    else:
                        counts["non_text_cells"] += 1
                        expected.append((name, cell.coordinate, cell.value))
                    target_coords.add((name, cell.coordinate))
            report_sheets.append({
                "name": name,
                "header_row": spec["header_row"],
                "data_start_row": spec["data_start_row"],
                "data_end_row": spec["data_end_row"],
                "columns": list(spec["columns"]),
                "counts": counts,
            })
            for k in totals:
                totals[k] += counts[k]
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if totals["changed_cells"] + totals["unchanged_text_cells"] + totals["blank_cells"] \
            + totals["non_text_cells"] + totals["formula_cells"] != totals["selected_cells"]:
        print("ERROR: 内部计数恒等式不成立，拒绝交付", file=sys.stderr)
        return 3

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(out_path)
    except OSError as exc:
        print(f"ERROR: 无法写出交付工作簿 {out_path}: {exc}", file=sys.stderr)
        return 2

    # ---- 保存后真实核验：重开输出与输入逐项比对 ----
    checks = []
    uncovered = [
        "未在原生Excel应用程序中做视觉渲染验证；样式保留结论来自openpyxl属性级比对",
        "未验证ZIP元数据与XML序列化顺序（契约R09明确不要求）",
        "公式仅在xlsx定义层面识别与保留（R06），未做重算引擎结果验证",
        "图表、图片、数据透视表等富对象不在本次契约与测试范围内，未验证其逐字节保真",
    ]

    try:
        wb_out = openpyxl.load_workbook(out_path, data_only=False)
        wb_in = openpyxl.load_workbook(in_path, data_only=False)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: 交付文件无法重新打开核验: {exc}", file=sys.stderr)
        return 3

    output_sha = sha256_file(out_path)

    # 1) 目标单元格 = 预期掩码/原值
    mismatch_target = []
    blank_ok = lambda want, got: want == got or (want == "" and got is None)
    for title, coord, want in expected:
        got = wb_out[title][coord].value
        if not blank_ok(want, got):
            mismatch_target.append((title, coord))
    checks.append({
        "name": "target_cells_match_expected",
        "status": "PASS" if not mismatch_target else "FAIL",
        "evidence": f"重开 {out_path} 核对 {len(expected)} 个选择单元格的目标值与预期一致；不一致 {len(mismatch_target)} 处",
    })

    # 2) 非目标单元格值完全一致（全簿逐格）
    compared, mismatch_nontarget = 0, []
    for title in wb_in.sheetnames:
        ws_in, ws_out = wb_in[title], wb_out[title]
        for row in ws_in.iter_rows():
            for cell in row:
                compared += 1
                if (title, cell.coordinate) in target_coords:
                    continue
                got = ws_out[cell.coordinate].value
                if not blank_ok(cell.value, got):
                    mismatch_nontarget.append((title, cell.coordinate))
    checks.append({
        "name": "non_target_values_preserved",
        "status": "PASS" if not mismatch_nontarget else "FAIL",
        "evidence": f"重开输入 {in_path}（sha256 {input_sha_before}）与输出 {out_path}（sha256 {output_sha}），全簿 {len(wb_in.sheetnames)} 个工作表逐格比对 {compared} 个单元格的值；非目标不一致 {len(mismatch_nontarget)} 处",
    })

    # 3) 样式与布局保持（R09）
    style_compared, style_mismatch = 0, []
    layout_ok = True
    if wb_in.sheetnames != wb_out.sheetnames:
        layout_ok = False
    for title in wb_in.sheetnames:
        if wb_in[title].sheet_state != wb_out[title].sheet_state:
            layout_ok = False
        if layout_sig(wb_in[title]) != layout_sig(wb_out[title]):
            layout_ok = False
        for row in wb_in[title].iter_rows():
            for cell in row:
                style_compared += 1
                if style_sig(cell) != style_sig(wb_out[title][cell.coordinate]):
                    style_mismatch.append((title, cell.coordinate))
    checks.append({
        "name": "styles_and_layout_preserved",
        "status": "PASS" if (layout_ok and not style_mismatch) else "FAIL",
        "evidence": f"重开输出 {out_path}（sha256 {output_sha}）与输入逐格比对 {style_compared} 个单元格的字体/填充/边框/对齐/数字格式，及表顺序、表状态、合并区域、冻结窗格、行列宽高；样式不一致 {len(style_mismatch)} 处，布局一致={layout_ok}",
    })

    # 4) 输入文件未被改动（R01）
    input_sha_after = sha256_file(in_path)
    checks.append({
        "name": "input_unchanged",
        "status": "PASS" if input_sha_before == input_sha_after else "FAIL",
        "evidence": f"处理前后输入SHA256一致: {input_sha_before}",
    })

    checks.append({
        "name": "deliverable_hash_recorded",
        "status": "PASS",
        "evidence": f"交付工作簿 SHA256: {output_sha}（实际交付路径: {out_path}）",
    })

    # 6) 全簿单元格存储类型与Excel表格定义保持（R06/R09）
    type_compared, type_mismatch = 0, []
    table_defs_in = {}
    table_defs_out = {}
    for title in wb_in.sheetnames:
        ws_in, ws_out = wb_in[title], wb_out[title]
        for row in ws_in.iter_rows():
            for cell in row:
                type_compared += 1
                if cell.data_type != ws_out[cell.coordinate].data_type:
                    type_mismatch.append((title, cell.coordinate))
        table_defs_in[title] = {
            tname: (ws_in.tables[tname].ref,
                    ws_in.tables[tname].tableStyleInfo.name
                    if ws_in.tables[tname].tableStyleInfo else None)
            for tname in ws_in.tables
        }
        table_defs_out[title] = {
            tname: (ws_out.tables[tname].ref,
                    ws_out.tables[tname].tableStyleInfo.name
                    if ws_out.tables[tname].tableStyleInfo else None)
            for tname in ws_out.tables
        }
    tables_same = table_defs_in == table_defs_out
    table_count = sum(len(v) for v in table_defs_in.values())
    checks.append({
        "name": "types_and_tables_preserved",
        "status": "PASS" if (tables_same and not type_mismatch) else "FAIL",
        "evidence": f"重开输入与输出逐格比对 {type_compared} 个单元格的存储类型（data_type），类型不一致 {len(type_mismatch)} 处；逐表比对Excel表格定义（表名/范围/样式）共 {table_count} 个，定义一致={tables_same}",
    })

    identity = (totals["changed_cells"] + totals["unchanged_text_cells"]
                + totals["blank_cells"] + totals["non_text_cells"]
                + totals["formula_cells"] == totals["selected_cells"])
    checks.append({
        "name": "counting_identity",
        "status": "PASS" if identity else "FAIL",
        "evidence": f"报告 {report_path} 的totals：changed {totals['changed_cells']} + unchanged_text {totals['unchanged_text_cells']} + blank {totals['blank_cells']} + non_text {totals['non_text_cells']} + formula {totals['formula_cells']} = selected {totals['selected_cells']}；恒等式成立={identity}，可由报告totals逐字段复算",
    })
    all_pass = all(c["status"] == "PASS" for c in checks)

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "input_sha256": input_sha_before,
        "output_sha256": output_sha,
        "masking": dict(m),
        "sheets": report_sheets,
        "totals": totals,
        "checks": checks,
        "uncovered": uncovered,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "status": "OK" if all_pass else "CHECKS_FAILED",
        "delivery": {
            "input_workbook": str(in_path),
            "output_workbook": str(out_path),
            "report_file": str(report_path),
        },
        "input_sha256": input_sha_before,
        "output_sha256": output_sha,
        "totals": totals,
        "checks": [{"name": c["name"], "status": c["status"], "evidence": c["evidence"]}
                   for c in checks],
        "uncovered": uncovered,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if all_pass else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
