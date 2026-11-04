# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

CAND = "何晓明"
doc = Document()

# 全局字体
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

for s in doc.sections:
    s.top_margin = Cm(2.2); s.bottom_margin = Cm(2.2)
    s.left_margin = Cm(2.5); s.right_margin = Cm(2.5)

def set_cn(run, font='宋体'):
    run.font.name = 'Calibri'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font)

def h1(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True; r.font.size = Pt(14); r.font.color.rgb = RGBColor(0x1F,0x49,0x7D)
    set_cn(r, '黑体')
    p.space_before = Pt(6)
    return p

def h2(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True; r.font.size = Pt(11.5)
    set_cn(r, '黑体')
    return p

def para(text, bold=False, size=10.5):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold; r.font.size = Pt(size)
    set_cn(r)
    return p

# ===== 封面标题 =====
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("候选人评估报告")
r.bold = True; r.font.size = Pt(22); set_cn(r, '黑体')
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("应聘岗位：硬件产品经理（广州 15-25K）")
r.font.size = Pt(12); set_cn(r)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("候选人：%s    评估日期：2026年10月22日" % CAND)
r.font.size = Pt(10.5); set_cn(r)
doc.add_paragraph()

# ===== 一、评估结论 =====
h1("一、评估结论")
p = para("【推荐面试】", bold=True)
r = p.runs[0]; r.font.size = Pt(12); r.font.color.rgb = RGBColor(0x00,0x70,0xC0)
para("候选人何晓明与硬件产品经理岗位整体匹配度高。其拥有10年以上产品管理经验，专业方向为电子科学与技术，近两年主导L4级无人安防巡逻机器人及配套AI平台从0到1落地并实现商用（首年销售额破千万元），与岗位“机器人、智能装备行业经验者优先”的加分项直接吻合；常用工具（Axure、Visio、XMind、墨刀）与岗位要求完全对应；PMP持证，具备软硬件协同交付、供应商与客户对接、全生命周期项目管理经验。建议安排面试，重点核实硬件技术协议理解深度及委外合同管理经验。")

# ===== 二、候选人基本信息 =====
h1("二、候选人基本信息")
tbl = doc.add_table(rows=5, cols=4)
tbl.style = 'Table Grid'; tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
info = [
    ("姓名", "何晓明", "性别", "女"),
    ("学历/专业", "桂林电子科技大学 · 电子科学与技术 · 学士", "现居地", "广州 黄埔"),
    ("工作年限", "10年以上产品管理经验（2013年至今）", "资质证书", "PMP、CET-4、C1驾照"),
    ("当前职务", "广东戬神科技 · 产品经理（2024.08至今）", "政治面貌", "中共党员"),
    ("行业背景", "机器人/无人驾驶、IoT智能硬件、安防、政企数字化", "联系电话", "13535588948"),
]
for i, row in enumerate(info):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = ""
        r = cell.paragraphs[0].add_run(val)
        r.font.size = Pt(10); set_cn(r)
        if j % 2 == 0:
            r.bold = True
doc.add_paragraph()

# ===== 三、任职要求逐条匹配 =====
h1("三、任职要求逐条匹配分析")
rows = [
    ("任职要求", "候选人情况", "匹配判断"),
    ("1. 本科及以上，自动化/电子/电气/机电/计算机相关专业",
     "桂林电子科技大学本科，电子科学与技术专业，专业对口",
     "✔ 符合"),
    ("2. 4年以上产品管理经验，优秀的文档编写与管理能力，机器人/智能装备行业经验优先",
     "10年以上产品经验；长期输出PRD、需求规格书、竞品分析、原型等文档；近期主导L4级无人安防巡逻机器人0到1落地，机器人行业经验直接命中优先项",
     "✔ 优于要求"),
    ("3. 较强的抗压、沟通、协调与组织能力，团队合作精神",
     "长期统筹软件、硬件、结构、设计、测试、运营等多团队协同；对接上游供应商与终端客户；跨部门、跨公司沟通经验丰富",
     "✔ 符合"),
    ("4. 思路清晰细致，责任心强，良好的统筹计划能力",
     "PMP持证；具备产品全生命周期管理经验（金升阳期间负责路线图规划、立项到停产清库存）；IoT项目全流程管控（预研、立项、排期、交付、迭代）",
     "✔ 符合"),
    ("5. 熟练使用Axure、Visio、Xmind等原型/流程/思维导图工具",
     "简历明确列出熟练使用Axure、Visio、XMind、墨刀",
     "✔ 完全符合"),
]
tbl = doc.add_table(rows=len(rows), cols=3)
tbl.style = 'Table Grid'
for i, row in enumerate(rows):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = ""
        r = cell.paragraphs[0].add_run(val)
        r.font.size = Pt(9.5); set_cn(r)
        if i == 0:
            r.bold = True
tbl.columns[0].width = Cm(4.2); tbl.columns[1].width = Cm(8.2); tbl.columns[2].width = Cm(2.6)
for row in tbl.rows:
    row.cells[0].width = Cm(4.2); row.cells[1].width = Cm(8.2); row.cells[2].width = Cm(2.6)
doc.add_paragraph()

# ===== 四、岗位职责匹配 =====
h1("四、岗位职责匹配分析")
rows = [
    ("岗位职责", "候选人对应经验", "匹配度"),
    ("1. 硬件产品规划、设计与定义，原型设计及文档撰写",
     "无人安防巡逻机器人0到1规划：主导产品定义、路线图制定、外观/结构/硬件功能设计；输出产品方案、PRD及原型；IoT产品需求定义、PRD、原型、推送设计",
     "高"),
    ("2. 需求调研、需求书撰写、路线图规划、行业性能指标与技术框架调研",
     "多段经历覆盖市场/用户/竞品分析；金升阳期间主导产品路线图规划、市场调研、需求转化；申迪期间负责智能化软硬件平台需求调研与方案设计",
     "高"),
    ("3. 对接产品需求与技术协议并转化为内部开发需求，跟进交付后运行状态",
     "具备软硬件协同交付与IoT生态对接经验（对接小米生态链、云米IoT平台）；云米期间跟踪上市后问题并快速迭代；戬神期间基于用户反馈持续迭代平台及产品",
     "较高（技术协议深度待面试核实）"),
    ("4. 产品培训、资料整理等管理工作",
     "云米IoT管理平台项目负责组织交付验收与内部培训；广电银通期间负责产品规划与培训；需求文档、投标材料等资料管理经验丰富",
     "高"),
    ("5. 委外项目需求整理、项目对接、合同编制与项目管理",
     "有上下游供应商筛选与对接经验（UWB定位方案供应商筛选、智慧监控供应商对接）；PMP项目管理背景；但简历未明确体现合同编制经验",
     "中等（合同编制待核实）"),
]
tbl = doc.add_table(rows=len(rows), cols=3)
tbl.style = 'Table Grid'
for i, row in enumerate(rows):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = ""
        r = cell.paragraphs[0].add_run(val)
        r.font.size = Pt(9.5); set_cn(r)
        if i == 0:
            r.bold = True
tbl.columns[0].width = Cm(4.2); tbl.columns[1].width = Cm(9.0); tbl.columns[2].width = Cm(3.0)
for row in tbl.rows:
    row.cells[0].width = Cm(4.2); row.cells[1].width = Cm(9.0); row.cells[2].width = Cm(3.0)
doc.add_paragraph()

# ===== 五、核心优势 =====
h1("五、核心优势")
for t in [
    "1. 行业经验高度对口：近两年主导L4级无人安防巡逻机器人从0到1规划与商用落地，产品首年销售额突破千万元，并落地湖南、新疆、广东、广西、江苏等数十家公安机构；另有无人环保走航机器人（单台最高182万元）落地经验，机器人与智能装备行业背景在候选人群中属稀缺加分项。",
    "2. 软硬件复合能力：覆盖IoT智能硬件、机器人整机、软件平台与app/小程序，具备硬件、结构、嵌入式与软件团队的统筹经验，能胜任软硬件协同交付类硬件产品管理。",
    "3. 工具链与文档能力扎实：熟练使用Axure、Visio、XMind、墨刀，长期输出PRD、需求规格书、竞品分析、原型等规范化文档，符合岗位对文档编写与管理的要求。",
    "4. 项目管理与统筹能力：PMP持证，具备从0到1到规模化的全生命周期管理经验，产品交付与商业化业绩可量化（米家净水器单品双十一销售额3亿元、设备激活百万级）。",
    "5. 外部协同经验丰富：长期对接上游供应商与终端客户，具备售前支持、投标技术支撑经验，有利于委外项目对接与技术协议沟通。",
]:
    para(t)

# ===== 六、风险与待核实事项 =====
h1("六、风险与待核实事项")
for t in [
    "1. 委外合同管理经验待核实：简历体现供应商对接与项目管理，但未明确合同编制、商务条款把控经验，建议面试追问委外项目合同编制与商务谈判的具体案例。",
    "2. 硬件技术深度需确认：候选人为电子科学与技术专业出身，但近十年工作偏产品定义与协同管理，建议核实其对硬件性能指标（如传感器、控制器、通信协议、功能安全等）的理解深度，以及撰写技术协议、转化开发需求的实际能力。",
    "3. 职业稳定性观察：2019.04-2020.02在申迪任职仅约10个月，2024年前后经历一次跳槽，建议了解离职原因与稳定性预期（当前公司任职2年+，整体稳定性尚可）。",
    "4. 行业跨度大但安防机器人场景偏C端/B端政企：需确认其产品方法论与贵司智能装备产品线的契合度，及对产品成本、供应链管控的参与深度。",
    "5. 薪资与到岗：简历未标注期望薪资，需在初面沟通15-25K区间及到岗时间的匹配度。",
]:
    para(t)

# ===== 七、面试建议 =====
h1("七、面试建议（建议提问方向）")
for t in [
    "1. 请展开介绍L4级无人安防巡逻机器人项目：产品定义中的关键技术指标取舍、与硬件/结构/算法团队的协作分工、以及交付后性能跟踪机制。",
    "2. 是否参与过技术协议/技术合同的编制与评审？请举例说明如何将客户技术协议转化为内部开发需求。",
    "3. 委外/供应商管理经验：如何进行供应商筛选、验收标准制定与交付风险管控？是否处理过合同纠纷或交付延期？",
    "4. 硬件知识考察：以巡逻机器人为例，说明其核心性能指标（续航、防护等级、定位精度、通信方式等）的定义依据与测试验证方法。",
    "5. 了解离职动机、期望薪资区间（对照15-25K）及到岗时间。",
]:
    para(t)

# ===== 八、综合评分 =====
h1("八、综合评分（满分5分）")
rows = [
    ("评估维度", "评分", "说明"),
    ("专业与学历", "5.0", "电子科学与技术本科，专业对口"),
    ("产品管理经验年限", "5.0", "10年以上，远超4年要求"),
    ("机器人/智能装备行业经验", "4.5", "L4安防巡逻机器人直接相关，属优先加分项"),
    ("文档编写与管理能力", "4.5", "PRD/需求规格书/竞品分析产出丰富"),
    ("工具使用（Axure/Visio/Xmind）", "5.0", "完全符合"),
    ("软硬件协同与技术协议转化", "4.0", "有软硬件协同与IoT对接经验，协议深度待核实"),
    ("委外项目管理（含合同编制）", "3.5", "有供应商对接与项目管理，合同编制经验待核实"),
    ("沟通协调与统筹能力", "4.5", "多团队/跨公司协同经验丰富，PMP持证"),
    ("综合匹配度", "4.5 / 5.0", "推荐面试"),
]
tbl = doc.add_table(rows=len(rows), cols=3)
tbl.style = 'Table Grid'
for i, row in enumerate(rows):
    for j, val in enumerate(row):
        cell = tbl.cell(i, j)
        cell.text = ""
        r = cell.paragraphs[0].add_run(val)
        r.font.size = Pt(9.5); set_cn(r)
        if i == 0 or (i == len(rows)-1):
            r.bold = True
tbl.columns[0].width = Cm(5.5); tbl.columns[1].width = Cm(3.0); tbl.columns[2].width = Cm(8.0)
for row in tbl.rows:
    row.cells[0].width = Cm(5.5); row.cells[1].width = Cm(3.0); row.cells[2].width = Cm(8.0)
doc.add_paragraph()

# ===== 落款 =====
p = para("评估说明：本报告基于候选人简历与岗位JD的书面比对，供初筛参考；最终录用决策需结合面试与背调结果。")
r = p.runs[0]; r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x80,0x80,0x80)

doc.save('/workspace/outputs/何晓明_候选人评估报告.docx')
print('saved')
