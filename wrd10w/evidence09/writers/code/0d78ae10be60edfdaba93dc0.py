# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
import os

os.makedirs("/workspace/outputs", exist_ok=True)

doc = Document()

# 全局字体：中文宋体，西文 Times New Roman
style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(12)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

def set_para(p, align=None, indent=True, spacing=1.5):
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = spacing
    if indent:
        pf.first_line_indent = Cm(0.74)
    return p

def add_run(p, text, bold=False, size=12, font_ea="宋体"):
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.element.rPr.rFonts.set(qn("w:eastAsia"), font_ea)
    r.font.size = Pt(size)
    r.bold = bold
    return r

# 标题
p = doc.add_paragraph()
set_para(p, WD_ALIGN_PARAGRAPH.CENTER, indent=False)
add_run(p, "投资承诺函", bold=True, size=16, font_ea="黑体")
p.paragraph_format.space_after = Pt(18)

# 称谓
p = doc.add_paragraph()
set_para(p, WD_ALIGN_PARAGRAPH.LEFT, indent=False)
add_run(p, "致：西安戴维新材料有限公司")

# 正文
body = [
    "嘉兴湃圃春之阳创业投资合伙企业（有限合伙）（以下简称“本合伙企业”）就参与贵公司本轮融资事宜，郑重承诺如下：",
    "一、本合伙企业同意参与西安戴维新材料有限公司本轮融资。",
    "二、本合伙企业拟投资金额初步确定为不超过人民币3,000万元，对应西安戴维新材料有限公司投前估值不超过人民币6亿元。",
    "三、本承诺函所载投资金额、估值等均为初步安排，具体以双方最终达成的交易文件为准。",
]
for t in body:
    p = doc.add_paragraph()
    set_para(p)
    add_run(p, t)

# 落款
p = doc.add_paragraph()
set_para(p, WD_ALIGN_PARAGRAPH.RIGHT, indent=False)
p.paragraph_format.space_before = Pt(24)
add_run(p, "嘉兴湃圃春之阳创业投资合伙企业（有限合伙）")

p = doc.add_paragraph()
set_para(p, WD_ALIGN_PARAGRAPH.RIGHT, indent=False)
add_run(p, "年　　月　　日")

doc.save("/workspace/outputs/投资承诺函.docx")
print("saved")
