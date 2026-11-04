# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

doc = Document()

# Default font: SimSun via eastasia
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(12)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

def add_para(text, align=None, bold=False, indent=True, space_after=6, size=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.5
    if align is not None:
        p.alignment = align
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.85)
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = 'Times New Roman'
    run.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    return p

# Title
title = add_para('投资承诺函', align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, indent=False, size=16, space_after=18)
title.paragraph_format.space_before = Pt(6)

add_para('西安戴维新材料有限公司：')

add_para('嘉兴湃圃春之阳创业投资合伙企业（有限合伙）（以下简称“本企业”）经审慎研究，现就参与贵公司本轮融资事宜郑重承诺如下：')

add_para('一、本企业同意参与西安戴维新材料有限公司本轮融资。')

add_para('二、本企业本轮投资金额初步确定为不超过人民币3,000万元，对应西安戴维新材料有限公司投前估值不超过人民币6亿元。')

add_para('三、上述投资金额及估值安排系初步确定，具体以本企业与贵公司最终达成的交易文件为准。')

add_para('特此承诺。', space_after=24)

# Signature block
p = add_para('出具主体：嘉兴湃圃春之阳创业投资合伙企业（有限合伙）', align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False)
p = add_para('日期：2026年10月21日', align=WD_ALIGN_PARAGRAPH.RIGHT, indent=False)

doc.save('/workspace/outputs/投资承诺函.docx')
print('saved')
