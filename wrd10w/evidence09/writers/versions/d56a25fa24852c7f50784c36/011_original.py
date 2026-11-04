# -*- coding: utf-8 -*-
"""生成 AI 客服系统商业案例报告 (.docx)"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

FONT = "Noto Sans CJK SC"

doc = Document()

# 全局样式
style = doc.styles["Normal"]
style.font.name = FONT
style.font.size = Pt(11)
style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)

def set_run(run, size=11, bold=False, color=None):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    if color:
        run.font.color.rgb = RGBColor(*color)

def heading(text, level=1):
    p = doc.add_paragraph()
    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        set_run(r, size=18, bold=True)
    else:
        sizes = {1: 14, 2: 12}
        r = p.add_run(text)
        set_run(r, size=sizes.get(level, 12), bold=True, color=(0x1F, 0x4E, 0x79))
        p.paragraph_format.space_before = Pt(14 if level == 1 else 8)
        p.paragraph_format.space_after = Pt(6)
    return p

def para(text, bold_prefix=None, size=11):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.4
    if bold_prefix:
        r = p.add_run(bold_prefix)
        set_run(r, size=size, bold=True)
    r = p.add_run(text)
    set_run(r, size=size)
    return p

def bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing = 1.4
    p.paragraph_format.space_after = Pt(3)
    if bold_prefix:
        r = p.add_run(bold_prefix)
        set_run(r, bold=True)
    r = p.add_run(text)
    set_run(r)
    return p

# ===== 封面标题 =====
heading("引入AI客服系统商业案例报告", level=0)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("——20万元投资合理性论证")
set_run(r, size=12, color=(0x59, 0x59, 0x59))
p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p2.add_run("编制日期：2026年10月23日    计价单位：人民币")
set_run(r, size=10, color=(0x80, 0x80, 0x80))

# ===== 一、执行摘要 =====
heading("一、执行摘要", 1)
para("公司现有8人客服团队，月均处理工单3,000个，按人均月薪8,000元计，月度人力成本为64,000元。计划投入20万元引入AI客服系统，预计可自动处理60%的工单（1,800个/月）。")
para("经量化测算：系统上线后每月可节约人力成本38,400元，年节约460,800元，3年累计收益138.24万元。以20万元总投入计，3年周期ROI（投资回报率）达591.2%，净收益118.24万元；投资回收周期约为5.2个月（即第6个月内即可收回全部投入）。综上，本项目投入小、见效快、回报高，建议批准实施。")

# ===== 二、现状痛点 =====
heading("二、现状痛点", 1)
bullet("（月均3,000个工单全部依赖8名人工客服处理，人均月处理量达375个，工作负荷趋于饱和）", bold_prefix="人工压力大：")
bullet("（人工服务受工作时间限制，难以覆盖7×24小时服务需求，夜间与节假日响应滞后）", bold_prefix="响应时效受限：")
bullet("（月度人力成本64,000元，年支出76.8万元；业务量每增长一步，均需同步增员，成本线性上升）", bold_prefix="成本刚性增长：")
bullet("（重复性、标准化问题占比高，人工处理一致性差，高峰期排队等待时间长，客户满意度承压）", bold_prefix="服务质量波动：")

# ===== 三、方案概述 =====
heading("三、方案概述", 1)
para("引入AI客服系统，通过智能语义理解与知识库匹配，自动应答客户咨询并处理标准化工单。核心设定如下：")
bullet("（系统预计自动处理60%的工单，即1,800个/月；剩余1,200个/月复杂工单由人工处理）", bold_prefix="自动化比例：")
bullet("（一次性投入20万元，含软件许可与部署费用；实施培训等成本已包含，不计其他隐性支出）", bold_prefix="投入构成：")
bullet("（节约的人力转投复杂工单处理与客户关怀，AI承接高频重复咨询并实现7×24小时即时响应）", bold_prefix="人机协同：")

# ===== 四、量化效益分析 =====
heading("四、量化效益分析", 1)
para("测算口径：人均月薪8,000元，8人团队月人力成本64,000元；AI替代60%工单量对应节约60%人力成本，即38,400元/月；投资总额20万元；测算周期3年（36个月）。")

rows = [
    ["测算口径", "成本节约", "效率增益", "ROI", "回收期"],
    ["月度", "38,400元（人力成本下降60%）", "自动处理1,800单/月，人工工单降至1,200单/月", "—", "—"],
    ["年度", "460,800元", "等效处理能力提升150%（可支撑7,500单/月）", "—", "—"],
    ["3年累计", "1,382,400元", "7×24小时即时响应，首响时间趋近于零", "591.2%（净收益1,182,400元）", "约5.2个月（第6个月内收回全部投入）"],
]

table = doc.add_table(rows=len(rows), cols=5)
table.style = "Table Grid"
table.alignment = WD_TABLE_ALIGNMENT.CENTER
widths = [Cm(2.2), Cm(4.2), Cm(4.2), Cm(3.6), Cm(3.6)]
for i, row_data in enumerate(rows):
    row = table.rows[i]
    for j, text in enumerate(row_data):
        cell = row.cells[j]
        cell.width = widths[j]
        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
        r = cp.add_run(text)
        set_run(r, size=10, bold=(i == 0))
        if i == 0:
            from docx.oxml import OxmlElement
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:fill"), "1F4E79")
            cell._tc.get_or_add_tcPr().append(shd)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

para("")
para("ROI =（3年累计总收益138.24万元 − 总投入20万元）÷ 总投入20万元 × 100% = 591.2%。投资回收期 = 总投入20万元 ÷ 月节约38,400元 ≈ 5.21个月，即系统上线后约第6个月实现盈亏平衡。", bold_prefix="计算说明：")

# ===== 五、风险与应对建议 =====
heading("五、风险与应对建议", 1)
rows2 = [
    ["风险", "影响", "应对建议"],
    ["AI识别准确率不达预期", "自动处理率低于60%，节约缩水", "上线前充分训练知识库，灰度发布，逐月监控自动解决率并持续调优"],
    ["复杂问题误转接或答非所问", "客户体验受损，投诉上升", "设置置信度阈值，低置信度自动转人工，保留人工兜底通道"],
    ["客服团队抵触与人员波动", "过渡期服务质量不稳", "提前沟通转岗安排，将人工重心转向高价值服务，配套激励方案"],
    ["数据安全与合规风险", "客户信息泄露隐患", "明确数据脱敏与权限管控要求，纳入采购合同与验收标准"],
    ["业务量快速增长超预期", "AI容量不足需追加投入", "选择支持弹性扩容的方案，合同中锁定扩容单价"],
]
table2 = doc.add_table(rows=len(rows2), cols=3)
table2.style = "Table Grid"
table2.alignment = WD_TABLE_ALIGNMENT.CENTER
w2 = [Cm(4.0), Cm(4.5), Cm(9.3)]
for i, row_data in enumerate(rows2):
    row = table2.rows[i]
    for j, text in enumerate(row_data):
        cell = row.cells[j]
        cell.width = w2[j]
        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
        r = cp.add_run(text)
        set_run(r, size=10, bold=(i == 0))
        if i == 0:
            from docx.oxml import OxmlElement
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:fill"), "1F4E79")
            cell._tc.get_or_add_tcPr().append(shd)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

para("")
para("综合以上分析，本项目以20万元投入换取月度38,400元的确定性人力成本节约，回收期仅约5.2个月，3年ROI达591.2%，同时显著提升工单处理效率与服务覆盖能力。在落实上述风险应对措施的前提下，建议公司尽快批准立项并推进实施。", bold_prefix="结论与建议：")

import os
os.makedirs("/workspace/outputs", exist_ok=True)
out = "/workspace/outputs/AI客服系统商业案例报告.docx"
doc.save(out)
print("saved:", out)
