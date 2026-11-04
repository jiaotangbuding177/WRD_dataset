# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

def set_font(run, name='微软雅黑', size=10.5, bold=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn('w:eastAsia'), name)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)

def add_para(doc, text, size=10.5, bold=False, style=None, align=None):
    p = doc.add_paragraph(style=style)
    r = p.add_run(text)
    set_font(r, size=size, bold=bold)
    if align is not None:
        p.alignment = align
    return p

def add_heading(doc, text, level=1):
    p = doc.add_heading('', level=level)
    r = p.add_run(text)
    set_font(r, size=14 if level == 1 else 12, bold=True, color=(0x1F, 0x4E, 0x79))
    return p

def add_table(doc, rows):
    t = doc.add_table(rows=len(rows), cols=3)
    t.style = 'Table Grid'
    widths = [Pt(115), Pt(240), Pt(115)]
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            c = t.cell(i, j)
            c.width = widths[j]
            c.text = ''
            r = c.paragraphs[0].add_run(cell)
            set_font(r, size=9.5, bold=(i == 0))
    return t

# ============ Report 1: 肖豪 ============
doc = Document()
add_para(doc, '候选人评估报告', size=18, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
add_para(doc, '应聘岗位：硬件产品经理（广州，15-25K）', size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
add_para(doc, '候选人：肖豪　|　评估日期：2026-10-21　|　评估依据：候选人简历与岗位JD逐项对照', size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

add_heading(doc, '一、候选人基本信息')
add_table(doc, [
    ['项目', '简历信息', '岗位要求对照'],
    ['学历/专业', '本科，海南师范大学（省重点），自动化专业（2009.09-2013.07）', '本科及以上，自动化/电子/电气/机电/计算机相关专业：符合'],
    ['工作年限', '8年产品经验；2014.07起任售前方案设计师，2018.05起先后在高新兴科技、佳都科技任产品经理', '4年以上产品管理经验：符合'],
    ['专业资质', 'NPDP、PMP、系统集成项目管理师、产品市场管理等证书', '加分项'],
    ['求职意向', '产品经理/AI产品经理，期望薪资面议，一周内到岗', '到岗时间有优势'],
])

add_heading(doc, '二、与岗位JD逐项对照')
add_table(doc, [
    ['岗位要求', '简历对应情况', '匹配判断'],
    ['1. 学历/专业要求', '本科，自动化专业', '符合'],
    ['2. 4年以上产品管理经验', '约8年产品经验（2018年至今专职产品经理），历任两家上市公司产品经理', '符合'],
    ['3. 文档编写与管理能力', '独立完成PRD需求文档、竞品分析、产品路线图、交互原型、项目落地方案', '符合'],
    ['4. 原型/流程/思维导图工具（Axure、Visio、Xmind）', '简历明确列出Axure、Visio、XMind，另有FigmaAI、墨刀，并掌握Python/JavaScript', '符合'],
    ['5. 机器人、智能装备行业经验（优先）', '以轨道交通、智慧城市、院校数据中台等软件平台/AI产品为主；硬件相关经验集中在“车载超融合一体机”项目（统筹整机硬件、嵌入式设计，主导SIL2功能安全认证，硬件成本下降38%）及智慧城市传感器/终端接入', '部分符合：有车载硬件一体化产品经验，但无机器人/智能装备直接行业经验'],
    ['6. 产品规划、需求调研、需求书、路线图', '多个项目体现完整产品规划与需求定义能力（MPIS平台、数据中台、产教评系统等）', '符合'],
    ['7. 对接需求与技术协议，转化为开发需求', '有制定全线网通信协议、系统对接接口规范经验；掌握Python可自主核对接口逻辑', '符合'],
    ['8. 产品培训、资料整理管理', '简历未明确提及产品培训与资料管理职责', '信息不足'],
    ['9. 委外项目需求整理、对接、合同编制与项目管理', '持有PMP及系统集成项目管理师证书，项目统筹能力强；但简历未明确提及委外/外包管理与合同编制经历', '部分覆盖：项目管理资质符合，委外与合同经验信息不足'],
    ['10. 沟通、协调、抗压、统筹能力', '跨线路多系统统筹、两级分权运营架构设计、多团队落地经验可佐证；无直接自述材料', '基本符合（以项目经历间接佐证）'],
])

add_heading(doc, '三、综合评价')
add_para(doc, '优势：', bold=True)
add_para(doc, '1. 学历专业对口，8年产品经验远超岗位要求，产品方法论体系完整（NPDP/PMP持证）；', style='List Bullet')
add_para(doc, '2. 工具链完全匹配（Axure/Visio/Xmind均熟练），文档与原型能力强；', style='List Bullet')
add_para(doc, '3. 具备硬件产品经验亮点：车载超融合一体机项目统筹整机硬件与嵌入式功能设计，主导SIL2功能安全认证，有明确硬件降本量化成果；对传感器、智能终端、设备全生命周期管理有实践；', style='List Bullet')
add_para(doc, '4. 轨道交通行业背景与机器人/智能装备场景（车载设备、无人驾驶列车场景）有一定相邻性。', style='List Bullet')
add_para(doc, '不足与风险：', bold=True)
add_para(doc, '1. 整体履历偏软件平台/AI大模型产品（RAG、数据中台），专职硬件产品经验占比较小，硬件供应链、结构/电子工程深度需面试验证；', style='List Bullet')
add_para(doc, '2. 无机器人、智能装备行业直接经验；', style='List Bullet')
add_para(doc, '3. 委外项目管理与合同编制、产品培训资料管理等职责在简历中无明确覆盖。', style='List Bullet')

add_heading(doc, '四、结论与建议')
add_para(doc, '推荐结论：建议推荐面试（匹配度：较高）。', bold=True)
add_para(doc, '候选人在学历、专业、年限、工具、文档与产品规划能力上全面达标，且有车载硬件一体化产品的真实交付经验，与“硬件产品经理”岗位核心要求基本吻合；其软件/AI背景属于额外加分项。建议面试重点考察：①车载一体机项目中硬件统筹的实际深度（与结构/电子/嵌入式团队的协作方式）；②机器人/智能装备领域的学习意愿与知识迁移能力；③委外/供应商管理与合同编制经验；④从软件产品转型硬件产品主导的动机与稳定性。')

doc.save('outputs/候选人评估报告_肖豪_硬件产品经理.docx')
print('saved report 1')

# ============ Report 2: 何晓明 ============
doc = Document()
add_para(doc, '候选人评估报告', size=18, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
add_para(doc, '应聘岗位：硬件产品经理（广州，15-25K）', size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
add_para(doc, '候选人：何晓明　|　评估日期：2026-10-21　|　评估依据：候选人简历与岗位JD逐项对照', size=10, align=WD_ALIGN_PARAGRAPH.CENTER)

add_heading(doc, '一、候选人基本信息')
add_table(doc, [
    ['项目', '简历信息', '岗位要求对照'],
    ['学历/专业', '桂林电子科技大学，电子科学与技术，学士', '本科及以上，电子相关专业：符合'],
    ['工作年限', '10年以上产品经验；2013.07起历任金升阳科技（产品管理）、电信规划设计院（需求分析师）、广电银通（产品经理）、申迪计算机（产品经理）、云米科技（IoT产品经理，2020.3-2024.7）、广东戬神科技（产品经理，2024.8至今）', '4年以上产品管理经验：远超要求'],
    ['专业资质', 'PMP证书、CET-4、C1驾照', '加分项'],
    ['现居地', '广州黄埔', '本地到岗便利'],
])

add_heading(doc, '二、与岗位JD逐项对照')
add_table(doc, [
    ['岗位要求', '简历对应情况', '匹配判断'],
    ['1. 学历/专业要求', '本科，电子科学与技术专业', '符合'],
    ['2. 4年以上产品管理经验', '10年以上产品经验，覆盖IoT、机器人、智能软硬件、政企数字化', '符合（超出）'],
    ['3. 机器人、智能装备行业经验（优先）', '负责L4级无人安防巡逻机器人0到1规划与商用落地（主导外观设计、结构设计、硬件功能设计），首年销售额破千万，落地数十家公安机构；另有无人环保走航机器人（单台最高182万）', '高度符合：直接命中优先项'],
    ['4. 文档编写与管理能力', '持续输出产品方案、PRD、原型、需求规格书、解决方案；搭建项目流程管理系统', '符合'],
    ['5. 原型/流程/思维导图工具（Axure、Visio、Xmind）', '专业技能明确列出Axure、Visio、XMind、墨刀', '符合'],
    ['6. 产品规划、需求调研、路线图', '多段经历体现市场/用户/竞品分析、产品定义、路线图制定、需求转化', '符合'],
    ['7. 对接需求与技术协议，转化为开发需求；交付后跟进', '统筹软件、硬件、设计、测试、运营团队实现全流程闭环交付；对接上下游供应商与终端客户；跟踪上市后问题并快速迭代（米家净水器等）', '符合'],
    ['8. 产品培训、资料整理管理', '云米IoT管理平台项目中“组织交付验收与内部培训”；广电银通期间负责产品规划与培训', '符合'],
    ['9. 委外项目需求整理、对接、合同编制与项目管理', '擅长多团队协同、供应商/客户对接、项目全生命周期管理（PMP持证）；协助投标材料制作；但简历未明确提及合同编制经历', '基本符合；合同编制经验信息不足'],
    ['10. 沟通、协调、抗压、统筹能力', '跨公司/跨部门大规模资源协调（协调上百个单品上线IoT平台、小米生态链多方协同），项目经历与自我评价均有佐证', '符合'],
])

add_heading(doc, '三、综合评价')
add_para(doc, '优势：', bold=True)
add_para(doc, '1. 与岗位高度对口：10年+产品经验且直接覆盖机器人（L4安防巡逻机器人、环保走航机器人）与智能软硬件，正中“机器人、智能装备行业经验优先”；', style='List Bullet')
add_para(doc, '2. 硬件产品全流程实战：从0到1主导机器人外观/结构/硬件功能设计，协调供应链与供应商，实现研发到商用闭环，有明确商业业绩（首年千万级）；', style='List Bullet')
add_para(doc, '3. 工具链完全匹配，软硬件协同与IoT生态对接能力强；', style='List Bullet')
add_para(doc, '4. PMP持证，具备多团队协同与供应商/客户对接的项目管控经验，契合委外项目对接职责；现居广州黄埔，本地稳定性好。', style='List Bullet')
add_para(doc, '不足与风险：', bold=True)
add_para(doc, '1. 委外项目中的合同编制职责无明确经历，需面试确认；', style='List Bullet')
add_para(doc, '2. 现任公司（2024.8至今）任职时间较短，离职原因需面试了解；', style='List Bullet')
add_para(doc, '3. 职业经历跨度较大（金融设备、家电IoT、安防机器人），需确认其在机器人/智能装备方向的长期职业规划。', style='List Bullet')

add_heading(doc, '四、结论与建议')
add_para(doc, '推荐结论：强烈建议优先安排面试（匹配度：高）。', bold=True)
add_para(doc, '候选人学历专业对口、年限远超要求，且具备与本岗位最贴近的机器人产品0到1全流程经验（含硬件设计统筹与供应商管理），文档、工具、沟通协调各项要求均有直接证据支撑，是本批候选人中与岗位匹配度更高者。建议面试重点考察：①委外/外包项目管理与合同编制的实际经验；②当前任职较短的离职原因与稳定性；③15-25K薪资区间的期望匹配度；④在安防机器人之外向智能装备领域迁移的意愿。')

doc.save('outputs/候选人评估报告_何晓明_硬件产品经理.docx')
print('saved report 2')
