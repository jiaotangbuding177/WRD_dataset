# -*- coding: utf-8 -*-
"""生成：候选人左_终面面试提纲.docx（线上面试，30分钟，结构化问题）"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml.ns import qn

FONT = "Noto Sans CJK SC"

def set_font(doc):
    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

def add_h(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for r in h.runs:
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        r.font.color.rgb = RGBColor(0x1F, 0x3B, 0x5C)
    return h

def add_p(doc, text, bold=False, size=10.5, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    r.font.name = FONT
    r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    r.font.size = Pt(size)
    r.bold = bold
    return p

def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    r.font.name = FONT
    r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    r.font.size = Pt(10.5)
    return p

doc = Document()
set_font(doc)

add_h(doc, "候选人左 · 终面面试提纲（AI产品经理岗）", 0)
add_p(doc, "面试形式：线上视频面试  |  时长：不超过30分钟  |  面试官：创始人张彦斌  |  地点：线上（终面原约张江双子塔A塔现场，按用户要求调整为线上执行）", size=9)
add_p(doc, "候选人画像提示：科莱特外包驻场百度张江任AI产品运营；前初创公司圆圈圈产品助理；主导中小测数字员工项目需求分析；期望薪资14K；自评产品能力3分，欠缺0到1系统化视角。终面核心目标：验证0到1产品思维、独立负责意愿与团队匹配度。", size=9)

def section(title, minutes, items, probe=None):
    add_h(doc, title, 1)
    add_p(doc, "时长：约%d分钟" % minutes, bold=True)
    for q, note in items:
        add_bullet(doc, q)
        if note:
            add_p(doc, "考察点：" + note, size=9)
    if probe:
        add_p(doc, "追问提示：" + probe, size=9)

section("一、开场与经历确认", 3, [
    ("请用2分钟简单介绍从圆圈圈到目前百度驻场的经历主线。", "表达与逻辑主线是否清晰。"),
    ("圆圈圈检验检测系统项目当时为什么停滞？如果重来，你会在哪个环节做不同的决策？", "归因方式：是客观环境归因还是有自我反思与改进方案。"),
], probe="注意其外包身份下与百度正式员工协作的真实边界，避免把团队成果完全记在自己名下。")

section("二、AI产品专业能力（核心板块）", 10, [
    ("中小测数字员工项目中，你独立完成的需求分析与产品方案，最终交付物是什么形态？开发按你的方案执行时出现过哪些偏差，你怎么处理？", "验证“独立完成”的真实颗粒度与需求落地能力。"),
    ("你把运营流程拆成7个环节评估AI接入，请完整讲一个环节从评估到上线的决策过程：投入产出怎么算？没接入的那个环节你是如何向业务方解释的？", "成本收益判断能力、向上/横向沟通说服能力。"),
    ("聚类不准确问题的排查：请举一个具体bad case，从“大模型语义理解→embedding聚类→RAG召回阈值→最终Prompt”链路中定位到根因，到优化后效果提升多少？", "排查链路是背概念还是真做过；是否有量化结果意识。"),
    ("你说AI产出的PRD比人工更好，那AI在PRD上出过什么错或遗漏？你如何校验和修改AI产出？", "是否真正把AI当工具而非依赖；文档质量把控能力（对应JD“会写PRD”）。"),
], probe="若回答停留在流程描述，追问具体数据：评估的7个环节各多少人天、聚类准确率优化前后数值。")

section("三、0到1产品思维情景题", 6, [
    ("情景题：公司正在从教育垂域向知识密集型研发行业拓展（如某军工/生物医药研发企业），假设由你负责前两周的需求调研，你会怎么安排？第一步做什么？", "0到1调研方法论：是否先搞清业务流程与用户角色，再谈AI方案。"),
    ("如果调研发现客户提的5个需求里研发只能做2个，你如何排优先级并向客户解释？", "对应JD“参与优先级讨论”“跟进商务对齐交付”。"),
], probe="候选人自认欠缺0到1视角，此题看其自学与迁移能力，接受思路不完美但不能空洞。")

section("四、用户共情与自驱验证", 4, [
    ("举一个你从用户反馈中发现问题、坚持推动研发改变的例子，中途遇到什么阻力？", "共情力与推动力（对应JD“站在用户视角”“自驱主动”）。"),
    ("技术公众号运营的粉丝量/阅读量大概什么量级？哪一篇效果最好，为什么？", "内容能力真实性与数据敏感度（对应加分项）。"),
])

section("五、动机、稳定性与匹配度", 5, [
    ("从百度外包体系跳到6人创业团队，你预期最大的落差是什么？打算怎么应对？", "对创业公司真实预期，防止理想化。"),
    ("这个岗位除产品外需要承担运营、配合商务的工作（面试中已说明），你的接受度如何？规划怎么分配精力？", "与复合岗位定位对齐。"),
    ("期望14K的依据是什么？如果预算接近但略低，你怎么考虑？", "薪资弹性与谈判空间。"),
    ("未来1-3年你的职业目标是什么？如果半年内产品方向发生较大调整，你的态度是？", "稳定性与方向认同（其最看重“产品发展方向”，需确认与公司教育+AI FOR SCIENCE路线一致）。"),
])

section("六、快问快答与候选人提问", 2, [
    ("快问：你最常用的3个AI工具分别解决什么问题？最近一次因为AI而“多做的事”是什么？", "AI热情与使用心得的即时验证。"),
    ("候选人提问与意向确认：告知后续流程与反馈时间。", "候选人提问质量可作为判断参考。"),
])

add_h(doc, "附：面试官评估记录表", 1)

tbl = doc.add_table(rows=1, cols=4)
tbl.style = "Table Grid"
hdr = tbl.rows[0].cells
for i, t in enumerate(["评估维度", "权重", "评分（1-5）", "备注"]):
    p = hdr[i].paragraphs[0]
    r = p.add_run(t)
    r.bold = True
    r.font.name = FONT
    r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    r.font.size = Pt(10)
rows = [
    ("AI工具应用与技术链路理解", "30%", "", ""),
    ("0到1产品思维与需求分析", "25%", "", ""),
    ("用户共情与自驱性", "15%", "", ""),
    ("沟通表达与优先级判断", "15%", "", ""),
    ("动机稳定性与薪资匹配", "15%", "", ""),
]
for row in rows:
    cells = tbl.add_row().cells
    for i, t in enumerate(row):
        p = cells[i].paragraphs[0]
        r = p.add_run(t)
        r.font.name = FONT
        r.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        r.font.size = Pt(10)

add_p(doc, "")
add_p(doc, "综合结论：□ 推荐录用  □ 备选（说明条件）  □ 不推荐。综合分≥3.8且“0到1产品思维”不低于3分建议推荐。", size=9)
add_p(doc, "时间控制提示：板块二为必保板块，若超时优先压缩板块四；全程严格控制在30分钟内。", size=9)

doc.save("/workspace/outputs/候选人左_终面面试提纲.docx")
print("outline saved")
