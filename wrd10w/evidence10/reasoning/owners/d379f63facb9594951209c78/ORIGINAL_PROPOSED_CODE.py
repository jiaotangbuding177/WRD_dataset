import os, json, glob, zipfile
import xml.etree.ElementTree as ET

WS = os.environ.get('WORKSPACE', '.')
out_dir = os.path.join(WS, 'outputs')
os.makedirs(out_dir, exist_ok=True)

report = {'imports': {}, 'input': None, 'sheets': [], 'docx_probe': None}
for mod in ('openpyxl', 'docx', 'xlsxwriter'):
    try:
        __import__(mod)
        report['imports'][mod] = True
    except Exception as e:
        report['imports'][mod] = type(e).__name__ + ': ' + str(e)

cands = [p for p in sorted(glob.glob(os.path.join(WS, 'inputs', '**', '*.xlsx'), recursive=True)) if os.path.isfile(p)]
if not cands:
    cands = [p for p in sorted(glob.glob(os.path.join(WS, '**', '*.xlsx'), recursive=True)) if os.path.isfile(p)]
assert cands, 'no xlsx input found under WORKSPACE'
path = cands[0]
report['input'] = os.path.relpath(path, WS)

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def col_idx(ref):
    letters = ''.join(ch for ch in ref if ch.isalpha())
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1 if n else 0

with zipfile.ZipFile(path) as z:
    names = z.namelist()
    assert 'xl/workbook.xml' in names, 'xl/workbook.xml missing'
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    sheet_defs = [(s.get('name'), s.get(RNS + 'id')) for s in wb.iter(NS + 'sheet')]
    assert sheet_defs, 'no sheets declared'
    shared = []
    if 'xl/sharedStrings.xml' in names:
        ss = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in ss.iter(NS + 'si'):
            shared.append(''.join(t.text or '' for t in si.iter(NS + 't')))
    rels = {}
    if 'xl/_rels/workbook.xml.rels' in names:
        r = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        for rel in r:
            rels[rel.get('Id')] = rel.get('Target')
    for name, rid in sheet_defs:
        target = rels.get(rid, '')
        if target.startswith('/'):
            target = target[1:]
        elif not target.startswith('xl/'):
            target = 'xl/' + target
        if target not in names:
            report['sheets'].append({'name': name, 'error': 'sheet xml missing', 'target': target})
            continue
        sh = ET.fromstring(z.read(target))
        rows = []
        for row in sh.iter(NS + 'row'):
            cells = {}
            for c in row.iter(NS + 'c'):
                idx = col_idx(c.get('r') or '')
                v = c.find(NS + 'v')
                isel = c.find(NS + 'is')
                if v is not None and v.text is not None:
                    txt = shared[int(v.text)] if c.get('t') == 's' else v.text
                elif isel is not None:
                    txt = ''.join(t.text or '' for t in isel.iter(NS + 't'))
                else:
                    txt = ''
                cells[idx] = txt
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, '') for i in range(width)])
        report['sheets'].append({'name': name, 'total_rows': len(rows), 'header': rows[0] if rows else [], 'rows': rows[:60]})

assert report['sheets'], 'no sheets parsed'
assert any(s.get('total_rows', 0) > 0 for s in report['sheets']), 'all sheets empty'

ct = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
doc = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>probe</w:t></w:r></w:p></w:body></w:document>'
docx_path = os.path.join(out_dir, 'probe_min.docx')
with zipfile.ZipFile(docx_path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', ct)
    z.writestr('_rels/.rels', rels_xml)
    z.writestr('word/document.xml', doc)
with zipfile.ZipFile(docx_path) as z:
    assert z.testzip() is None, 'corrupt docx'
    assert 'word/document.xml' in z.namelist(), 'docx missing document.xml'
report['docx_probe'] = {'path': os.path.relpath(docx_path, WS), 'ok': True}

with open(os.path.join(out_dir, 'structure_report.json'), 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False))
