# -*- coding: utf-8 -*-
"""生成英语教案 docx（口语训练为重点环节）"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

CN = "宋体"
CN_HEI = "黑体"
EN = "Times New Roman"

doc = Document()

# 页面设置 A4
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.2)
sec.left_margin = sec.right_margin = Cm(2.5)

# 正文默认样式
style = doc.styles["Normal"]
style.font.name = EN
style.font.size = Pt(10.5)
style.element.rPr.rFonts.set(qn("w:eastAsia"), CN)

def set_font(run, size=10.5, bold=False, cn=CN, en=EN, color=None):
    run.font.name = en
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), cn)
    if color:
        run.font.color.rgb = RGBColor(*color)

def para(text="", size=10.5, bold=False, cn=CN, en=EN, align=None,
         space_after=4, indent=None, line=1.3):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line
    if align is not None:
        p.alignment = align
    if indent is not None:
        p.paragraph_format.first_line_indent = Pt(indent)
    r = p.add_run(text)
    set_font(r, size=size, bold=bold, cn=cn, en=en)
    return p

def heading(num, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(f"{num}　{text}")
    set_font(r, size=13, bold=True, cn=CN_HEI)
    return p

def sub(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    set_font(r, size=11.5, bold=True, cn=CN_HEI)
    return p

# ============ 标题 ============
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.paragraph_format.space_after = Pt(2)
r = t.add_run("英语教案")
set_font(r, size=20, bold=True, cn=CN_HEI)

subt = doc.add_paragraph(); subt.alignment = WD_ALIGN_PARAGRAPH.CENTER
subt.paragraph_format.space_after = Pt(8)
r = subt.add_run("（以口语训练为重点环节 · 一课时 45 分钟）")
set_font(r, size=12, bold=False, cn=CN)

# ============ 基本信息表 ============
info = doc.add_table(rows=4, cols=4)
info.style = "Table Grid"
info.alignment = WD_TABLE_ALIGNMENT.CENTER
rows = [
    ("课题", "Unit 6 I'm going to study computer science（Section A 1a–2c）", "年级", "八年级（初二）"),
    ("课型", "新授课·听说课", "课时", "第 1 课时（45 分钟）"),
    ("教材", "人教版《英语（Go for it!）》八年级上册", "授课语言", "英语为主，汉语辅助"),
    ("授课教师", "________", "授课班级", "________"),
]
for i, (a, b, c, d) in enumerate(rows):
    cells = info.rows[i].cells
    for j, txt in enumerate((a, b, c, d)):
        cell = cells[j]
        cell.paragraphs[0].text = ""
        r = cell.paragraphs[0].add_run(txt)
        bold = j % 2 == 0
        set_font(r, size=10.5, bold=bold, cn=CN_HEI if bold else CN)
for row in info.rows:
    row.cells[0].width = Cm(2.2); row.cells[1].width = Cm(7.3)
    row.cells[2].width = Cm(2.2); row.cells[3].width = Cm(3.8)

# ============ 一、教材分析 ============
heading("一", "教材分析")
para("本课选自人教版《英语（Go for it!）》八年级上册 Unit 6 I'm going to study computer science 的 Section A（1a–2c），核心语言功能是“谈论将来的打算（Talk about future intentions）”，核心句型为 “What are you going to be when you grow up?” “How are you going to do that?” 及 “be going to + 动词原形” 的用法。话题贴近学生生活，指向职业理想与人生规划，具有真实的交际价值和思想教育意义，为口语表达提供了丰富而真实的内容载体。", indent=21)

# ============ 二、学情分析 ============
heading("二", "学情分析")
para("八年级学生已掌握一般现在时与一般过去时，具备谈论职业类词汇的基础（如 doctor, teacher 等），求知欲强、乐于表达，但口语输出存在“敢听不敢说、能懂不会组句”的问题，部分学生存在怕错心理。本课通过低起点的机械操练逐步过渡到意义操练与自由表达，并借助 pair work、小组采访、报告展示等多样的口语活动，帮助学生在真实语境中开口、在合作中纠错提升。", indent=21)

# ============ 三、教学目标 ============
heading("三", "教学目标")
sub("（一）语言能力")
para("1. 能正确听、说、读、写职业与规划类核心词汇：computer programmer, engineer, pilot, scientist, violinist, cook, doctor, driver 等；", indent=21)
para("2. 能在口语交际中熟练运用目标句型：What are you going to be when you grow up? — I'm going to be… / How are you going to do that? — I'm going to…；", indent=21)
para("3. 能听懂谈论未来打算的对话，抓住关键信息；能就“职业理想及实现途径”进行 2–3 轮连贯口头问答，并作简短的口头报告。", indent=21)
sub("（二）文化意识与思维品质")
para("1. 初步了解中外青少年谈论职业理想的表达习惯，树立正确的职业观；", indent=21)
para("2. 能结合自身实际，有条理地说明“理想职业 + 实现路径”，发展逻辑思维与批判性思维。", indent=21)
sub("（三）学习能力与情感态度")
para("1. 通过结对合作、小组采访等活动，学会倾听、追问与合作学习；", indent=21)
para("2. 敢于开口用英语表达自己的理想，增强学习自信心，体会“理想需要行动去实现”的道理。", indent=21)

# ============ 四、教学重难点 ============
heading("四", "教学重难点")
para("教学重点：", bold=True, indent=21)
para("1. 职业类词汇的正确认读与运用；2. 运用目标句型进行口头问答：“What are you going to be…? / How are you going to do that?”。", indent=21)
para("教学难点：", bold=True, indent=21)
para("1. be going to 结构中动词原形的正确使用，避免 “I'm going to be going to” 等误用；2. 将机械问答发展为围绕话题的连贯口语输出（追问、补充理由、连贯报告）。", indent=21)

# ============ 五、教学方法 ============
heading("五", "教学方法与准备")
para("教学方法：任务型语言教学（TBLT）＋交际语言教学（CLT），辅以情景教学与小组合作学习；教师语言与学生活动均以英语为主。", indent=21)
para("教学准备：多媒体课件、单词图卡、职业调查表（Worksheet）、“梦想职业卡”若干、计时器。", indent=21)
para("口语训练总体设计思路：本课约 70% 的时间用于学生开口操练，遵循 “跟读模仿 → 机械问答 → 意义问答 → 真实交际 → 口头报告” 五级梯度，环环相扣、逐级加大语言自主度。", indent=21)

# ============ 六、教学过程 ============
heading("六", "教学过程（重点环节：口语训练）")

tbl = doc.add_table(rows=1, cols=4)
tbl.style = "Table Grid"
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr = tbl.rows[0].cells
for c, txt in zip(hdr, ("环节/时间", "教师活动", "学生活动", "设计意图")):
    c.paragraphs[0].text = ""
    r = c.paragraphs[0].add_run(txt)
    set_font(r, size=10.5, bold=True, cn=CN_HEI)

def add_stage(a, b, c, d, highlight=False):
    row = tbl.add_row().cells
    for cell, txt in zip(row, (a, b, c, d)):
        cell.paragraphs[0].text = ""
        parts = txt.split("\n")
        for k, part in enumerate(parts):
            p = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(part)
            set_font(r, size=9.5, bold=False, cn=CN)
    if highlight:
        for cell in row:
            tcPr = cell._tc.get_or_add_tcPr()
            from docx.oxml import OxmlElement
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:fill"), "FFF2CC")
            tcPr.append(shd)

add_stage(
    "Step 1\n热身导入\nWarm-up & Lead-in\n(5分钟)",
    "1. 播放英文歌曲《Be What You Wanna Be》片段，师生同唱。\n2. 展示工程师、飞行员、程序员等职业图片，用 “What does he/she do?” 快速热身，引出课题 “dream jobs”。",
    "跟唱歌曲，活跃气氛；看图抢答职业名称，激活已学词汇。",
    "创设轻松氛围，以旧引新，自然切入“理想职业”话题，为口语输出做词汇铺垫。")

add_stage(
    "Step 2\n词汇与句型呈现\nPresentation\n(8分钟)",
    "1. 借助图卡新授词汇：computer programmer, engineer, pilot, scientist, violinist, cook 等，采用 “Read after me → 高低音变声读 → 开火车读” 三轮操练。\n2. 教师示范目标句：I'm going to be a pilot when I grow up. 呈现 “be going to” 结构并板书句型框架。",
    "三轮跟读新词（注意 violinist 等重音）；观察句型框架，模仿教师语音语调朗读示范句。",
    "保证语音输入准确；词汇句型呈现后立即集体朗读，为后续口语操练夯实基础。")

add_stage(
    "Step 3\n【口语重点①】机械问答操练\nDrill: Pair Q&A\n(7分钟)",
    "1. 带领全班用 “Chain Drill” 开火车问答：教师问一名学生 “What are you going to be when you grow up?”，该生答后反向提问下一名同学，句子依次传递。\n2. 布置 Pair Work：同桌一人问 “How are you going to do that?”，一人答 “I'm going to study math really hard.”，1 分钟后交换角色。\n3. 巡视纠音，收集典型错误，操练后集中正音。",
    "开火车快速接龙问答，人人开口；同桌按屏幕提示句型互相问答并交换角色，练习 “be going to” 的准确输出。",
    "【口语重点环节】低难度的机械操练保证全班参与度，实现“人人开口”，在受控操练中内化核心句型、突破难点①。", highlight=True)

add_stage(
    "Step 4\n听力输入\nListening (1b, 2a–2b)\n(8分钟)",
    "1. 播放 1b 录音，学生听录音连线“人物—理想职业”。\n2. 播放 2a–2b 录音，完成 “How are they going to do that?” 表格；听后师生口头核对：T: What is Tina going to be? Ss: She's going to be…",
    "听录音抓关键信息完成任务；听后用完整句口头回答教师提问，复述听力人物的职业打算。",
    "以听促说：听力文本本身即目标句型的范例，口头核对环节让学生再次开口输出。")

add_stage(
    "Step 5\n【口语重点②】真实交际\nRole-play & Interview\n(10分钟)",
    "1. Role-play：三人一组，其中一人扮演“小记者”，采访两位组员的职业理想及实现途径，要求每人至少问 2 个问题，可追问 “Why?”。\n2. 发放调查表，组内完成 “Dream Job Interview”，记录姓名、理想职业、实现途径。\n3. 教师巡视，提供句型支架（You may ask: What…/How…/Where…），并请 1–2 组上台展示采访对话。",
    "小组内开展真实采访交际，围绕话题进行 3 轮以上自由问答并记录信息；两组上台展示，其余学生认真倾听。",
    "【口语重点环节】从受控操练走向真实交际，学生在有信息差的任务中自由运用目标语言，突破难点②，培养交际策略与合作能力。", highlight=True)

add_stage(
    "Step 6\n【口语重点③】口头报告\nGroup Report\n(5分钟)",
    "1. 布置 Report 任务：依据调查表，用第三人称作连贯口头报告，给出支架 “In my group, … is going to be a/an… He/She is going to… That sounds…”.\n2. 各组 1 分钟准备后，随机抽 2–3 名学生面向全班报告，师生按“声音响亮、句子完整、有理有据”三条标准口头点评。",
    "组内先互说再推选代表，用连贯语段报告组内同学的梦想与计划；倾听并互评他人报告。",
    "【口语重点环节】实现“对话→语段”的输出升级，训练连贯表达与第三人称转换，师生共评使口语评价可视化。", highlight=True)

add_stage(
    "Step 7\n小结与情感升华\nSummary\n(2分钟)",
    "1. 师生共同回顾本课核心词汇与句型（指板书）。\n2. 情感升华：Where there is a will, there is a way. 引导学生认识“为理想付诸行动”的重要性。",
    "跟随教师齐读核心句型；齐读谚语，体会其含义。",
    "梳理知识结构，落实情感目标，实现语言学习与育人价值融合。")

for row in tbl.rows:
    row.cells[0].width = Cm(2.6)
    row.cells[1].width = Cm(5.6)
    row.cells[2].width = Cm(4.2)
    row.cells[3].width = Cm(3.1)

para("注：表中底色标注的 Step 3、Step 5、Step 6 为本课口语训练的三个重点环节，分别对应“受控操练—真实交际—连贯输出”三个梯度。", size=9, indent=0)

# ============ 七、板书设计 ============
heading("七", "板书设计")
para("Unit 6  I'm going to study computer science", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
para("— What are you going to be when you grow up?", align=WD_ALIGN_PARAGRAPH.CENTER)
para("— I'm going to be a / an …  (pilot / engineer / programmer …)", align=WD_ALIGN_PARAGRAPH.CENTER)
para("— How are you going to do that?", align=WD_ALIGN_PARAGRAPH.CENTER)
para("— I'm going to … (study… / practice… / take… lessons)", align=WD_ALIGN_PARAGRAPH.CENTER)
para("Dream  →  Action!   (Where there is a will, there is a way.)", align=WD_ALIGN_PARAGRAPH.CENTER)

# ============ 八、作业布置 ============
heading("八", "作业布置")
para("1. 基础作业（必做）：抄写并朗读本课职业类词汇与目标句型各 3 遍，家长或同伴签字确认朗读；完成练习册 Section A 1a–2c 配套习题。", indent=21)
para("2. 口语作业（必做·重点）：录制 1 分钟左右的音频 “My Dream Job”，用 “be going to” 说说自己的职业理想及三条实现计划，次日课前在小组内播放互评。", indent=21)
para("3. 拓展作业（选做）：采访一位家人或朋友的职业理想，用英语写 3–5 句短文，下节课分享。", indent=21)

# ============ 九、教学反思 ============
heading("九", "教学反思（课后填写）")
para("1. 口语操练梯度是否合理？各层次学生是否都获得了开口机会？", indent=21)
para("2. “be going to + 动词原形” 的错误是否在操练中得到及时纠正？", indent=21)
para("3. 小组采访与报告环节的时间控制与参与面如何？需要在下一课时作哪些调整？", indent=21)

import os
os.makedirs("/workspace/outputs", exist_ok=True)
out = "/workspace/outputs/英语教案.docx"
doc.save(out)
print("saved:", out)
