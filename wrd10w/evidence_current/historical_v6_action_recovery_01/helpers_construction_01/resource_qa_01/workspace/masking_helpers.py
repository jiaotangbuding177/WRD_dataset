"""Scoped building blocks for Excel field masking.

validate_request checks only the required/basic Python types, ranges and
selection shape below. It is NOT a full JSON Schema validator and does not
reject additional properties; the caller must perform full schema validation.
resolve_path is lexical resolution, NOT path authorization or overwrite safety.
classify supports ordinary cells, formulas, blank, strings and non-string
values; error/rich-text or application-specific cell types need separate review.
layout_sig is only a partial layout fingerprint: no table definitions, rich
objects, complete styles, recalculation or Excel visual-render guarantee.
This module does not modify/write a workbook or generate a report/skill.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

REQUEST_SCHEMA_VERSION = "data_field_mask_request_v1"


class ContractError(Exception):
    """Invalid required/basic parameter or header selection."""


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
