# -*- coding: utf-8 -*-
"""生成《云知师AI学生端应用场景》中文文档 (.docx)"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

DOC_PATH = "/workspace/outputs/云知师AI学生端应用场景文档.docx"
CJK = "Noto Sans CJK SC"


def set_cjk_font(run, name=CJK):
    run.font.name = name
    r = run._element.rPr
    rFonts = r.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = r.makeelement(qn('w:rFonts'), {})
        r.append(rFonts)
    rFonts.set(qn('w:eastAsia'), name)
    rFonts.set(qn('w:ascii'), name)
    rFonts.set(qn('w:hAnsi'), name)


def add_para(doc, text, size=11, bold=False, align=None, space_after=6,
             indent=False, color=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.4
    if indent:
        p.paragraph_format.first_line_indent = Pt(22)
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    set_cjk_font(run)
    return p


def add_heading(doc, text, level=1):
    sizes = {0: 20, 1: 16, 2: 13, 3: 12}
    colors = {0: (0x1F, 0x4E, 0x79), 1: (0x1F, 0x4E, 0x79),
              2: (0x2E, 0x6D, 0xA4), 3: (0x33, 0x33, 0x33)}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level <= 1 else 10)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(text)
    run.font.size = Pt(sizes[level])
    run.bold = True
    run.font.color.rgb = RGBColor(*colors[level])
    set_cjk_font(run)
    return p


def add_bullet(doc, text, prefix="· "):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(24)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.35
    run = p.add_run(prefix + text)
    run.font.size = Pt(11)
    set_cjk_font(run)
    return p


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # header
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        run.bold = True
        run.font.size = Pt(10.5)
        set_cjk_font(run)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = ""
            run = cell.paragraphs[0].add_run(val)
            run.font.size = Pt(10.5)
            set_cjk_font(run)
    if widths:
        for j, w in enumerate(widths):
            for r in table.rows:
                r.cells[j].width = Cm(w)
    return table


doc = Document()
# page margins
for sec in doc.sections:
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.5)

# ============ 封面标题 ============
add_para(doc, "云知师AI学生端应用场景文档", size=22, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10,
         color=(0x1F, 0x4E, 0x79))
add_para(doc, "—— 基于“课前·课中·课后·家校·终身发展”全链路闭环的学生视角详述 ——",
         size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6,
         color=(0x59, 0x59, 0x59))
add_para(doc, "依据公开资料整理编写 | 2026年10月", size=10.5,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18,
         color=(0x80, 0x80, 0x80))

# ============ 文档说明 ============
add_heading(doc, "文档说明", 1)
add_para(doc, "云知师AI是由华东师范大学数据科学与工程学院团队联合其衍生企业（上海胆大求索科技有限公司）研发的教育垂直领域智能体协同平台，已入驻国家智慧教育公共服务平台“AI试验场”模块的“教师教学”核心板块。平台以“用AI点亮每一间教室”为愿景，围绕课前备课、课中AI增强教学、课后个性化辅导、课外家校管理、教师终身发展五大场景构建教学闭环，目前已集成40余项AI应用，覆盖约80%的备课与教学工作外延场景。", indent=True)
add_para(doc, "需要说明的是：云知师AI以教师端工具为主，学生端的使用场景主要通过“教师端生成资源—课堂互动—课后反馈”的链路辐射到学生。本文档从学生视角出发，系统梳理学生在云知师AI支撑的教学全流程中能够获得的应用场景，供参考。本文依据公开报道与官方页面资料整理，具体功能以平台实际版本为准。", indent=True)

# ============ 一、产品概述 ============
add_heading(doc, "一、产品概述", 1)
add_heading(doc, "1.1 平台定位", 2)
add_para(doc, "云知师AI定位为面向教育场景的AI赋能平台，支持无代码创作与项目式协作，构建了覆盖“备课—授课—评估”全流程的智能体协同体系。平台深度贴合新课标与中小学教材体系，依托华东师范大学百万级教学资源库与前沿教育理论，服务对象覆盖K12、高职、高校等多个学段。", indent=True)
add_heading(doc, "1.2 与学生端的关系", 2)
add_para(doc, "平台虽然以教师为主要直接用户，但其五大场景闭环中的每一环都直接作用于学生的学习体验：课前环节为学生提供预习导学资源；课中环节重塑课堂互动样态；课后环节实现个性化辅导与分层作业；家校环节支撑学生成长的过程性反馈。据公开报道，平台已服务师生30万人次，用户覆盖26个省、64个市、250余所学校，并在贵州省28所本科及51所职业院校的数字素养通识课中落地使用。", indent=True)

# ============ 二、学生端应用场景总览 ============
doc.add_page_break()
add_heading(doc, "二、学生端应用场景总览", 1)
add_para(doc, "下表按教学全流程梳理云知师AI支撑下的学生端主要应用场景：", indent=True)
add_table(
    doc,
    ["教学环节", "学生端场景", "主要支撑功能", "典型学段"],
    [
        ["课前", "智能预习与导学", "思维导图一键生成、预习导学案", "K12全学段"],
        ["课中", "AI增强的互动课堂", "课堂随练、随堂检测、智能板书、跨学科资源", "K12/高职/高校"],
        ["课中", "项目化学习协作", "项目化学习教案与任务链、共享工作区", "小学高段—高校"],
        ["课后", "个性化辅导与答疑", "分层命题、个性化练习生成", "K12全学段"],
        ["课后", "错题巩固与知识补漏", "知识点关联出题、难度可调", "K12全学段"],
        ["复习", "复习卡片与知识梳理", "单元重点提炼、复习卡片生成", "K12全学段"],
        ["课外", "自主学习与AI素养培养", "无代码创作、数字素养通识课", "中学—高校"],
        ["课外", "学情反馈与家校协同", "班级成绩分析、学情报告", "K12全学段"],
        ["全程", "差异化学习支持", "千人千案个性化资源适配", "全学段"],
    ],
    widths=[2.2, 4.0, 5.6, 3.4],
)

# ============ 三、核心应用场景详解 ============
doc.add_page_break()
add_heading(doc, "三、核心应用场景详解", 1)

add_heading(doc, "3.1 课前：智能预习与导学", 2)
add_para(doc, "教师使用云知师AI的“一键生成思维导图”功能梳理课文知识点，输出知识框架结构图后，可直接下发给学生用于课前预习。学生在这一场景中的获益包括：", indent=True)
add_bullet(doc, "预习目标可视化：学生通过知识框架图提前了解本课的知识脉络与重点分布，带着结构化的“地图”进入课堂，预习不再盲目。")
add_bullet(doc, "导学任务个性化：教师基于AI生成的适配本班学情的导学案（可按不同层次调整），为不同基础的学生布置差异化预习任务，避免“一刀切”。")
add_bullet(doc, "预习负担减轻：AI提炼的预习材料短小精悍，学生无需在海量资料中自行筛选，预习效率显著提升。")
add_para(doc, "该场景对小学中高年级至高中学生尤为适用，是培养自主学习习惯的重要抓手。", indent=True)

add_heading(doc, "3.2 课中：AI增强的互动课堂", 2)
add_para(doc, "云知师AI对课中环节的增强，直接改变了学生的学习方式。据上海市建平实验中学教师反馈，AI赋能下课堂结构与互动样态已突破传统运行逻辑，引发主体关系、学习环境、评价机制的转型升级。学生端的具体场景包括：", indent=True)
add_bullet(doc, "随堂练习与即时检测：教师用“智能命题”功能现场生成随堂练习，学生当堂作答、即时反馈，错误点当堂暴露、当堂解决。")
add_bullet(doc, "多媒体学习资源：平台支持一键生成图文、音视频等内容，学生可以在课堂上接触更丰富的呈现形式（如情境动画、语音讲解），提升理解与专注度。")
add_bullet(doc, "跨学科课堂：AI辅助生成跨学科教学方案，学生在主题式课堂中打通学科壁垒，体验语文、科学、艺术等知识的融合应用。")
add_bullet(doc, "板书与笔记支撑：AI生成的知识结构图可直接用作课堂板书，学生笔记有清晰框架可依，课后整理负担降低。")

add_heading(doc, "3.3 课中进阶：项目化学习与协作探究", 2)
add_para(doc, "云知师AI支持项目化学习（PBL）教案创作与项目式协作、共享工作区，这是学生端最具深度的应用场景之一：", indent=True)
add_bullet(doc, "真实任务驱动：教师借助平台设计项目化学习任务链，学生围绕真实问题开展小组探究，从“听讲者”转变为“研究者”。")
add_bullet(doc, "协作与成果产出：依托共享工作区，学生小组可以协同收集资料、整理过程记录、完成项目成果（报告、展示文稿等），锻炼协作与表达能力。")
add_bullet(doc, "过程性指导：AI帮助教师为不同小组提供差异化的过程指导材料，使项目化学习不流于形式，让每一组学生都能获得与其进度匹配的支架。")
add_para(doc, "该场景适合小学高段、初高中综合实践活动以及高职、高校的实训课程。", indent=True)

add_heading(doc, "3.4 课后：个性化辅导与分层练习", 2)
add_para(doc, "“课后个性化辅导”是云知师AI五大闭环场景之一，也是学生端获益最直接的环节：", indent=True)
add_bullet(doc, "分层作业设计：教师使用“智能命题与分层出题”功能，依据知识点自动生成配套练习并调整难度，为不同水平的学生布置“跳一跳够得着”的作业，实现因材施教。")
add_bullet(doc, "精准补漏：针对随堂检测暴露的薄弱知识点，AI帮助教师快速生成针对性变式题，学生的错题不再是简单订正，而是被系统性地巩固。")
add_bullet(doc, "即时答疑资源：教师可将AI生成的解题思路与讲解材料分享给学生，学生在课后自主学习时获得“类一对一”的辅导支持。")
add_bullet(doc, "“千人千案”的个性化目标：平台AI模型具备持续学习与自我优化能力，通过真实教学数据反馈不断精进，最终指向每个学生匹配差异化学习资源的个性化教学目标。")

add_heading(doc, "3.5 复习与备考：知识梳理与复习卡片", 2)
add_para(doc, "围绕单元复习与考试备考，学生端场景包括：", indent=True)
add_bullet(doc, "复习卡片辅助记忆：教师用“制作复习卡片”功能提炼单元重点，生成便于携带与记忆的卡片式材料，学生可利用碎片时间完成单元复习。")
add_bullet(doc, "知识体系重构：借助AI梳理的知识框架图，学生在复习阶段能够把零散知识点串联成体系，从“记知识点”升级为“懂知识网”。")
add_bullet(doc, "模拟检测：教师依据考点智能组卷出题，学生通过仿真练习熟悉题型、检验复习效果，降低备考焦虑。")

add_heading(doc, "3.6 课外：自主学习与AI数字素养培养", 2)
add_para(doc, "云知师AI支持无代码创作，这一能力同样向学生的学习场景延伸，尤其在数字素养教育中已规模化落地——贵州省28所本科及51所职业院校的数字素养通识课即使用该平台，服务师生达30万人次：", indent=True)
add_bullet(doc, "数字素养通识学习：学生在课程中系统学习人工智能基础知识与AI工具使用方法，理解AI的能与不能，建立正确的AI观。")
add_bullet(doc, "无代码创作实践：学生无需编程基础即可用平台进行创意作品创作（如知识海报、学习小程序雏形等），实现“科学想象变成现实”，培养计算思维与创新意识。")
add_bullet(doc, "AI辅助自学能力：在教师引导下，学生学会借助AI工具开展资料检索、知识梳理与自我检测，掌握AI时代的基本学习技能。")

add_heading(doc, "3.7 学情反馈与家校协同中的学生支持", 2)
add_para(doc, "“课外家校管理”是五大闭环场景之一，学生是学情数据的最终受益者：", indent=True)
add_bullet(doc, "成绩分析反哺学习改进：教师使用“班级成绩分析”功能快速了解学生学习情况并针对性施教；学生由此获得更贴合自身实际的改进建议，而不是笼统的“要努力”。")
add_bullet(doc, "过程性成长记录：AI支撑下的作业、检测数据沉淀为学生的过程性画像，家长和教师能看见学生的成长趋势，减少唯分数评价带来的压力。")
add_bullet(doc, "家校学习衔接：家长通过学校下发的个性化学习建议，明确家庭辅导的方向，学生在家校两端获得一致的学习支持。")

add_heading(doc, "3.8 差异化与特殊学习需求支持", 2)
add_para(doc, "依托平台的智能体能力与教学资源库，学生端的差异化支持场景包括：", indent=True)
add_bullet(doc, "学习困难学生的补基支架：AI将知识点拆解为更细粒度的阶梯任务并降低题目难度，帮助基础薄弱学生逐步建立信心。")
add_bullet(doc, "学有余力学生的拓展资源：AI生成更高挑战度的跨学科探究任务与拓展阅读材料，让学有余力的学生“吃得饱”。")
add_bullet(doc, "不同教材版本与学段的适配：平台支持选定学段、学科、教材版本与章节生成内容，转学生、走班学生也能快速获得与新教材匹配的学习资源。")

# ============ 四、典型使用流程示例 ============
doc.add_page_break()
add_heading(doc, "四、典型使用流程示例", 1)

add_heading(doc, "流程一：一节常态课的学生端闭环", 2)
add_bullet(doc, "课前：教师用AI生成思维导图与预习导学案 → 学生按图预习，完成分层预习任务。")
add_bullet(doc, "课中：教师用AI生成随堂检测题 → 学生当堂作答，系统即时反馈，教师依据结果调整讲解节奏。")
add_bullet(doc, "课后：教师依据检测结果生成分层作业与错题变式 → 学生完成个性化练习，薄弱点得到针对性巩固。")

add_heading(doc, "流程二：单元复习阶段", 2)
add_bullet(doc, "教师用AI提炼单元重点生成复习卡片与知识框架图 → 学生借助卡片进行碎片化记忆、借助框架图构建知识体系。")
add_bullet(doc, "教师智能组卷进行单元模拟检测 → 学生自检复习效果，教师据此安排查漏补缺。")

add_heading(doc, "流程三：项目化学习单元", 2)
add_bullet(doc, "教师用“项目化学习教案创作”设计真实任务 → 学生分组进入共享工作区，明确分工与时间线。")
add_bullet(doc, "学生借助平台检索资料、协作产出成果 → 各组展示，AI辅助教师按多元维度评价。")
add_bullet(doc, "成果与数据沉淀 → 学生获得过程性评价反馈，反思改进。")

# ============ 五、应用价值 ============
add_heading(doc, "五、应用价值分析", 1)
add_table(
    doc,
    ["价值维度", "具体表现"],
    [
        ["减轻学习负担", "预习、复习材料由AI提炼精编，学生少做无效功；分层作业让练习量与难度更贴合个人实际。"],
        ["提升学习效率", "即时反馈缩短“出错—纠错”周期；知识框架与复习卡片让学习更有章法。"],
        ["促进教育公平", "平台已覆盖26个省250余所学校并向贵州等地数字素养课推广，偏远地区学生也能获得优质AI教育资源。"],
        ["培养面向未来的能力", "数字素养课程与无代码创作实践，让学生在使用AI中理解AI，养成AI时代的核心学习素养。"],
        ["支持因材施教", "“千人千案”的个性化资源适配，让不同层次学生获得匹配其水平的学习支持。"],
    ],
    widths=[3.6, 11.6],
)

# ============ 六、使用建议与注意事项 ============
add_heading(doc, "六、使用建议与注意事项", 1)
add_bullet(doc, "学生应在教师指导下使用相关功能，AI生成内容需经教师审核把关，避免未经甄别直接采信。")
add_bullet(doc, "低龄学生使用AI工具时，建议加强家长与教师的陪伴引导，注意用眼健康与使用时长管理。")
add_bullet(doc, "AI是学习的辅助而非替代：学生应先独立思考，再借助AI核对与拓展，防止形成依赖。")
add_bullet(doc, "涉及学生数据时，学校与教师应遵循国家关于未成年人个人信息保护的有关规定，规范采集与使用学情数据。")
add_bullet(doc, "本文档依据公开资料整理，平台功能迭代较快，实际可用的功能模块与访问方式以云知师AI官方平台（可通过国家智慧教育公共服务平台 www.smartedu.cn 的“AI试验场”模块访问）当前版本为准。")

# ============ 七、参考资料 ============
add_heading(doc, "七、参考资料来源", 1)
add_bullet(doc, "华东师范大学官网：《华东师大研发“云知师AI”入驻国家智慧教育公共服务平台》（www.ecnu.edu.cn，2026年1月）。")
add_bullet(doc, "云知师AI官方欢迎页面：smartedu-yunzhishi.zzz4ai.com。")
add_bullet(doc, "双师智教网站“双师智教&云知师AI”服务介绍页（shuangshizhijiao.com）。")
add_bullet(doc, "夜雨聆风学习网：《国家智慧教育平台官方AI备课工具——云知师AI备课》（2026年10月）。")
add_bullet(doc, "搜狐/腾讯新闻：《从6人团队到千校覆盖：她如何打造出教师的“AI神助”？》（2026年4月）。")

doc.save(DOC_PATH)
print("saved:", DOC_PATH)
