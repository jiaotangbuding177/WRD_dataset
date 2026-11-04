import os, re, json, zipfile
from xml.etree import ElementTree as ET

WS = os.environ.get("WORKSPACE", ".")
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS = {"m": MAIN[1:-1]}
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# --- locate input xlsx (future user parameter, discovered not hardcoded) ---
cands = []
for root, dirs, files in os.walk(WS):
    if os.sep + "outputs" in root:
        continue
    for f in files:
        if f.lower().endswith(".xlsx") and not f.startswith("~$"):
            cands.append(os.path.join(root, f))
assert cands, "no .xlsx input found under WORKSPACE"
path = sorted(cands)[0]
print("INPUT:", path)

# --- probe available xlsx libraries (u1) ---
libs = {}
for mod in ("openpyxl", "pandas", "xlrd"):
    try:
        __import__(mod)
        libs[mod] = True
    except Exception:
        libs[mod] = False
print("LIBS:", libs)

z = zipfile.ZipFile(path)
names = z.namelist()
assert "xl/workbook.xml" in names, "not a valid xlsx package"

def txt(el):
    return "".join(t.text or "" for t in el.iter(MAIN + "t"))

shared = []
if "xl/sharedStrings.xml" in names:
    ss = ET.fromstring(z.read("xl/sharedStrings.xml"))
    shared = [txt(si) for si in ss.findall("m:si", NS)]

wb = ET.fromstring(z.read("xl/workbook.xml"))
relmap = {}
if "xl/_rels/workbook.xml.rels" in names:
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.get("Id"): r.get("Target") for r in rels}
sheets = []
for s in wb.findall(".//m:sheets/m:sheet", NS):
    tgt = relmap.get(s.get(RNS + "id"), "")
    if tgt.startswith("/"):
        tgt = tgt.lstrip("/")
    elif not tgt.startswith("xl/"):
        tgt = "xl/" + tgt
    sheets.append((s.get("name"), tgt))
print("SHEETS:", sheets)
assert sheets, "no sheets found in workbook"

def col_letter(ref):
    m = re.match(r"([A-Z]+)", ref or "")
    return m.group(1) if m else ""

def read_rows(sheet_path):
    root = ET.fromstring(z.read(sheet_path))
    out = []
    for row in root.findall(".//m:sheetData/m:row", NS):
        cells = {}
        for c in row.findall("m:c", NS):
            ref, t = c.get("r") or "", c.get("t")
            v, isel = c.find("m:v", NS), c.find("m:is", NS)
            if t == "s" and v is not None:
                val = shared[int(v.text)]
            elif t == "inlineStr" and isel is not None:
                val = txt(isel)
            elif v is not None:
                val = v.text
            else:
                val = None
            if ref:
                cells[col_letter(ref)] = val
        out.append(cells)
    return out

PHONE = re.compile(r"1[3-9]\d{9}")
report = {}
for name, sp in sheets:
    rows = read_rows(sp)
    assert len(rows) >= 1, "sheet %s has no rows" % name
    header = rows[0] if rows else {}
    hdr_items = sorted(header.items(), key=lambda kv: (len(kv[0]), kv[0]))
    print("---", name, "rows:", len(rows))
    print("HEADER:", hdr_items)
    for r in rows[1:4]:
        print("SAMPLE:", sorted(r.items(), key=lambda kv: (len(kv[0]), kv[0])))
    phones = sum(1 for r in rows for v in r.values() if isinstance(v, str) and PHONE.search(v))
    report[name] = {"rows": len(rows), "header": hdr_items, "phone_cells": phones}

kw = ("客户", "单位", "名称", "公司", "付款")
cand_cols = {}
for name in report:
    cand_cols[name] = [c for c, v in report[name]["header"] if isinstance(v, str) and any(k in v for k in kw)]
print("NAME_COL_CANDIDATES:", cand_cols)
assert any(cand_cols.values()), "no name-like column header found; column mapping must be confirmed manually"

os.makedirs(os.path.join(WS, "outputs"), exist_ok=True)
with open(os.path.join(WS, "outputs", "structure_report.json"), "w", encoding="utf-8") as f:
    json.dump({"input": path, "libs": libs, "sheets": report, "name_col_candidates": cand_cols}, f, ensure_ascii=False, indent=2)
print("WROTE outputs/structure_report.json")
print("OK")
