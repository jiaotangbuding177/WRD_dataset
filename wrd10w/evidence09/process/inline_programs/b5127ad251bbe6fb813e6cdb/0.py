import docx
d = docx.Document('inputs/materials/conv_f4efc3b555dc/1_材料2.安徽中科微感股权投资合同20260721.docx')
lines = []
for i, p in enumerate(d.paragraphs):
    t = p.text.strip()
    if t:
        lines.append(t)
# also tables
for ti, tb in enumerate(d.tables):
    for r in tb.rows:
        cells = [c.text.strip() for c in r.cells]
        lines.append('[表格] ' + ' | '.join(cells))
text = '\n'.join(lines)
open('tmp/contract.txt','w',encoding='utf-8').write(text)
print(len(lines), 'lines,', len(text), 'chars')
