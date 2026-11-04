# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn

DOC_PATH = "/workspace/outputs/机械设计工程师岗位JD（完善版）.docx"

doc = Document()

# ---- base style: Noto Sans CJK SC ----
style = doc.styles["Normal"]
style.font.name = "Noto Sans CJK SC"
style.font.size = Pt(11)
style.element.rPr.rFonts.set(qn("w:eastAsia"), "Noto Sans CJK SC")

# page margins
for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)


def set_cn_font(run, name="Noto Sans CJK SC"):
    run.font.name = name
    run.element.rPr.rFonts.set(qn("w:eastAsia"), name)


def add_title(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(18)
    set_cn_font(run)


def add_heading(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    set_cn_font(run)


def add_para(text, indent=0.0, bullet=False, space_after=4):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.4
    pf.space_after = Pt(space_after)
    if indent:
        pf.left_indent = Cm(indent)
    run = p.add_run(text)
    run.font.size = Pt(11)
    set_cn_font(run)
    return p


# ---- title ----
add_title("机械设计工程师")

# subtitle line
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(10)
run = p.add_run("岗位说明书（Job Description）")
run.font.size = Pt(11)
run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
set_cn_font(run)

# ---- 岗位职责 ----
add_heading("一、岗位职责")

responsibilities = [
    "负责机器人机械系统的设计工作，涵盖概念设计、详细设计、原型制作及测试验证全流程；",
    "负责机械部件的选型、分析与计算，包括结构强度、应力分析、疲劳寿命分析及传动系统设计等；",
    "与电气、软件、算法、生产等部门紧密协同，确保机械设计满足整机系统需求，并能适应粉尘、高温、高湿、腐蚀等复杂恶劣场景；",
    "负责防爆壳体、密封防护等特殊结构设计，确保产品满足防爆认证、矿用安标等合规要求；",
    "主导解决产品开发过程中的技术难题，持续优化产品性能与可靠性，并有效降低制造成本；",
    "编写并维护各类技术文档，包括设计规格书、测试报告、用户手册等；",
    "持续跟踪行业动态，积极引入新技术、新材料、新工艺，不断提升产品竞争力。",
]
for i, item in enumerate(responsibilities, 1):
    add_para(f"{i}. {item}")

# ---- 任职要求 ----
add_heading("二、任职要求")

add_para("1. 教育背景", bullet=False, space_after=2)
add_para("机械工程或相关专业本科及以上学历；具有丰富现场场景经验者优先考虑。", indent=0.74)

add_para("2. 工作经验", bullet=False, space_after=2)
work_exp = [
    "8年以上机械设计领域工作经验，并具有相关应用场景经验；",
    "有轨道巡检机器人、轮式机器人、四足机器人等产品设计经验者优先；",
    "有重型设备、煤矿井下防爆设备、液压传动设备设计经验者优先。",
]
for item in work_exp:
    add_para("• " + item, indent=0.74)

add_para("3. 专业技能", bullet=False, space_after=2)
skills = [
    "精通CAD/CAM/CAE软件（如SolidWorks、AutoCAD、ANSYS等）；",
    "熟悉机械部件设计原理、制造工艺及材料选择；",
    "了解机械设计标准、规范及行业相关法规；",
    "具备良好的问题解决能力和创新思维。",
]
for item in skills:
    add_para("• " + item, indent=0.74)

add_para("4. 个人素质", bullet=False, space_after=2)
quality = [
    "积极主动、责任心强，能够在快节奏环境中保持高效工作；",
    "具有良好的团队合作精神，乐于分享知识、促进团队共同成长；",
    "对新技术充满热情，坚持持续学习，追求卓越。",
]
for item in quality:
    add_para("• " + item, indent=0.74)

doc.save(DOC_PATH)
print("saved:", DOC_PATH)
