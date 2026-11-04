from docx import Document
for f in ['/workspace/outputs/候选人评估报告_宋先生_生产制造运营总监.docx','/workspace/outputs/候选人评估报告_黄和芳_生产制造运营总监.docx']:
    d = Document(f)
    paras = [p.text for p in d.paragraphs if p.text.strip()]
    tables = len(d.tables)
    print(f.split('/')[-1], '| 段落数:', len(paras), '| 表格数:', tables)
    print('  标题:', paras[0], '|', paras[1])
    # spot check table content
    t = d.tables[0]
    print('  硬性对照表行数:', len(t.rows), '判定列:', [r.cells[3].text for r in t.rows[1:]])
