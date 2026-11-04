import sys, os, json, zipfile, re, glob

base = os.environ.get('WORKSPACE', os.getcwd())
candidates = []
if len(sys.argv) > 1:
    candidates = [sys.argv[1]]
else:
    candidates = glob.glob(os.path.join(base, 'inputs', '**', '*.docx'), recursive=True)
assert candidates, 'no docx input found under WORKSPACE/inputs'
path = candidates[0]
assert os.path.isfile(path), f'missing file: {path}'

with zipfile.ZipFile(path) as z:
    names = z.namelist()
    assert 'word/document.xml' in names, 'word/document.xml absent'
    xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
text = re.sub(r'<[^>]+>', '', xml)
text = re.sub(r'\s+', ' ', text).strip()
assert len(text) > 100, f'text too short: {len(text)}'

keywords = ['劳务费', '30%', '1000万', '300万', '里程碑', '设备', '材料', '测试化验', '其他费用', '预算', '专项', '自筹']
report = {'path': path, 'text_length': len(text), 'keyword_hits': {}, 'contexts': {}}
for kw in keywords:
    idxs = [m.start() for m in re.finditer(re.escape(kw), text)]
    report['keyword_hits'][kw] = len(idxs)
    report['contexts'][kw] = [text[max(0, i-100):i+160] for i in idxs[:3]]
assert any(v > 0 for v in report['keyword_hits'].values()), 'no budget keyword found in extracted text'

os.makedirs(os.path.join(base, 'outputs'), exist_ok=True)
out = os.path.join(base, 'outputs', 'docx_budget_probe.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])
