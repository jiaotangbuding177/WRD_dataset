# -*- coding: utf-8 -*-
"""生成英语教案 docx（口语训练重点课）。"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

CN_FONT = "Noto Sans CJK SC"
EN_FONT = "Times New Roman"

doc = Document()

# 页面设置 A4
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.4)
sec.top_margin = sec.bottom_margin = Cm(2.4)

# 默认样式
style = doc.styles["Normal"]
style.font.name = EN_FONT
style.font.size = Pt(11)
style.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
style.paragraph_format.line_spacing = 1.3

def set_run(run, size=11, bold=False, color=None, cn=CN_FONT, en=EN_FONT):
    run.font.name = en
    run.element.rPr.rFonts.set(qn("w:eastAsia"), cn)
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)

def para(text, size=11, bold=False, align=None, space_after=4, indent=None, color=None, en=EN_FONT):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run(r, size=size, bold=bold, color=color, en=en)
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if indent is not None:
        p.paragraph_format.first_line_indent = Pt(indent)
    return p

def heading(text, size=13):
    p = para(text, size=size, bold=True, space_after=6)
    p.paragraph_format.space_before = Pt(10)
    return p

def bullet(label, text, indent=21):
    p = doc.add_paragraph()
    r1 = p.add_run(label)
    set_run(r1, bold=True)
    r2 = p.add_run(text)
    set_run(r2)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.left_indent = Pt(indent)
    return p

# ===== 标题 =====
p = para("英语教案（口语训练重点课）", size=18, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)
p2 = para("Unit 6  I'm going to study computer science", size=14, bold=True,
          align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2, en=EN_FONT)
# 修正副标题字体（英文课名）
for r in p2.runs:
    r.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
para("（人教版《英语（Go for it!）》八年级上册 · Section A 第一课时 · 45分钟）",
     size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

# ===== 一、基本信息 =====
heading("一、基本信息")
info = doc.add_table(rows=4, cols=4)
info.style = "Table Grid"
info.alignment = WD_TABLE_ALIGNMENT.CENTER
info_data = [
    ("课题", "Unit 6  I'm going to study computer science（Section A 1a–2d）", "课型", "口语重点课（听说课）"),
    ("课时", "第 1 课时（45 分钟）", "授课对象", "初中八年级学生"),
    ("教材", "人教版《英语（Go for it!）》八年级上册", "授课教师", "＿＿＿＿＿＿"),
    ("教学环境", "多媒体教室（PPT、图片卡、任务单）", "班级规模", "约 40 人"),
]
for i, row in enumerate(info_data):
    for j, val in enumerate(row):
        cell = info.cell(i, j)
        cell.text = ""
        r = cell.paragraphs[0].add_run(val)
        set_run(r, size=10.5, bold=(j % 2 == 0))
        cell.paragraphs[0].paragraph_format.space_after = Pt(2)
for w, c in zip((2.4, 6.2, 2.4, 4.6), info.columns):
    for cell in c.cells:
        cell.width = Cm(w)

# ===== 二、教材分析 =====
heading("二、教材分析")
para("本课选自人教版八年级上册 Unit 6，核心话题为“谈论理想职业与人生规划”。Section A 部分呈现了 be going to 表达未来打算的核心句型，以及与职业相关的词汇（computer programmer, engineer, pilot, scientist 等）。话题贴近学生生活，表达需求真实，是开展大剂量、多形式口语训练的优质载体。本课时为单元第一课时，重在通过听说活动输入语言，并以课堂口头输出（pair work、role play、interview、report）为主轴，为后续读写课打下口语基础。", indent=21)

# ===== 三、学情分析 =====
heading("三、学情分析")
para("八年级学生已掌握一般现在时和一般将来时 will 的基本用法，具备初步的问答交流能力，词汇量足以支撑简单职业话题。但学生普遍存在“能听懂、不敢说、说得少”的问题，口语输出的流利度与互动性不足。因此本课采用低门槛、高频次、强互动的口语活动链（由机械操练到意义操练再到自由表达），并通过示范、脚手架（句型卡、思维导图）和小组激励降低开口焦虑，保证每个学生都有多次开口机会。", indent=21)

# ===== 四、教学目标 =====
heading("四、教学目标")
bullet("1. 语言能力目标：", "能正确听、说、认读职业类词汇 computer programmer, engineer, pilot, scientist, doctor, actor；能准确、流利地运用核心句型 “What are you going to be when you grow up?” “I'm going to be a(n) …” “How are you going to do that?” “I'm going to …” 进行有关理想职业与实现途径的问答。")
bullet("2. 学习能力目标：", "通过 pair work、chain drill、interview 等口语活动，学会借助句型支架和关键词组织口头表达；能在采访和汇报中主动追问、即兴应答。")
bullet("3. 思维品质目标：", "能够围绕“理想职业—实现路径”进行有条理的口头描述，形成“目标+措施”的逻辑表达框架。")
bullet("4. 文化意识与情感目标：", "树立理想并认识到理想需要行动支撑；在小组合作交流中增强开口自信，尊重并欣赏同伴的不同志向。")

# ===== 五、教学重难点 =====
heading("五、教学重难点")
bullet("教学重点：", "① 职业类核心词汇的听说与运用；② 核心句型 “What are you going to be…? / How are you going to do that?” 的准确朗读与流利问答。")
bullet("教学难点：", "① 在真实交际情境中主动、连贯地使用目标句型进行多轮对话，而非机械背句；② 口头表达中 be going to 与职业名词前冠词 a/an 的正确搭配，以及实现途径表达（study… really hard, take… lessons, practice… every day）的灵活运用。")

# ===== 六、教学方法 =====
heading("六、教学方法")
para("任务型语言教学法（TBLT）为主，情境交际法与小组合作学习为辅。以“班级梦想职业采访会”为大任务贯穿全课，采用“输入—操练—输出”的口语训练主线：教师示范 → 机械操练（准确）→ 意义操练（流利）→ 自由交际（创造）。", indent=21)

# ===== 七、教学过程 =====
heading("七、教学过程（口语训练为主线）")

process = [
    ("Step 1", "Warm-up & Lead-in\n热身导入", "3′",
     "① 播放 30 秒不同职业工作者工作的短视频/图片快闪（pilot, engineer, doctor…），学生看图快速抢答职业名称。\n② 教师自我示范：“When I was your age, I wanted to be a teacher. What about you?” 引出话题。",
     "用图片快闪激活背景词汇，营造开口氛围；抢答人人可参与，快速消除紧张感。"),
    ("Step 2", "Presentation\n新知呈现与输入", "8′",
     "① 借助图片与实物卡教学目标词汇：computer programmer, engineer, pilot, scientist, doctor, actor；采用“升降调跟读—开火车快读—看图抢说”三步操练读音。\n② 教师与一名优生合作示范对话：\nT: What are you going to be when you grow up?\nS: I'm going to be a computer programmer.\nT: How are you going to do that?\nS: I'm going to study computer science.\n③ 板书核心句型与 be going to 结构图，全班齐读两遍（注意 a/an 与语调）。",
     "词句结合输入；示范对话为后续操练提供清晰的语言支架。"),
    ("Step 3", "Mechanical Drills\n机械操练（口语训练①）", "5′",
     "① Chain drill 接龙：按座位依次问答 “What are you going to be when you grow up? — I'm going to be a(n) …”，速度逐渐加快。\n② Pair work 句型替换：同桌利用职业卡与途径卡随机抽卡造句，互相纠正 a/an 与动词搭配。",
     "高频次、低压力的封闭式操练，保证发音与结构准确，人人至少开口 3 次。"),
    ("Step 4", "Listening Practice\n听力感知与模仿", "6′",
     "① 完成 1b 听力：听录音圈出听到的职业，核对答案后跟读模仿录音中的语音语调。\n② 角色配音：同桌分角色朗读 1b 对话并交换角色，教师抽查 2 组展示。",
     "听后即说、跟读模仿，让学生习得地道语调，为自由表达蓄力。"),
    ("Step 5", "Meaningful Practice — Role Play\n意义操练·情境对话（口语训练②）", "8′",
     "情境任务“校园小记者”： Suppose you are a school reporter interviewing a student about his/her dream job. 同桌自选情境卡（含提示词：dream job / why / how / first step），编演不少于 4 个来回的对话，鼓励追问 “Why?” “When are you going to start?”。教师巡视指导，邀请 2–3 组上台展示，其他学生用“互评表”（内容、语音、流利度三星制）评价。",
     "在半开放情境中运用目标语言进行多轮交际，追问设计推动真实互动与思维参与。"),
    ("Step 6", "Free Production — Interview & Report\n自由表达·采访汇报（口语训练③，核心环节）", "10′",
     "① 4 人小组开展 “Dream Job Interview”：每人轮流当记者采访组内 1 名同伴，用采访记录单（Name / Dream job / How to do it / One question of your own）记录，追问问题由学生自创。\n② 每组推选 1 名代表面向全班做 30–45 秒汇报：“In our group, Linda is going to be a pilot. She is going to take flying lessons…”，要求至少用 3 个目标句型。\n③ 教师从流利度、句型使用、追问质量三方面即时点评表扬，评选“最佳记者”“最佳应答者”。",
     "从对话走向小组多向交际与成段口头输出，实现语言的真实运用；轮换记者保证均衡参与。"),
    ("Step 7", "Summary & Emotional Sublimation\n小结升华", "3′",
     "① 师生共同回顾板书，齐 chant：“Dream job, dream job, what are you going to be? / Study hard, practice more, I'm going to make it!”\n② 情感升华：Where there is a dream, there is a way — 理想更要靠行动实现。",
     "节奏化复现巩固句型；渗透情感目标，首尾呼应。"),
    ("Step 8", "Homework Assignment\n作业布置", "2′",
     "必做：① 口头作业——把课堂采访内容录成 1 分钟语音 “My friend's dream job”，发到班级群；② 书面作业——用 5 句话写下自己的理想职业及实现途径。\n选做：采访一位家人 “What did you want to be when you were young?”，下节课口头分享。",
     "口头作业延续口语训练重点，实现课内到课外的迁移；作业分层，兼顾不同水平学生。"),
]

for step, name, t, act, intent in process:
    p = doc.add_paragraph()
    r = p.add_run(f"{step}  {name}（{t}）")
    set_run(r, size=11.5, bold=True)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    pl = p.add_run("\n")
    # 活动内容
    p1 = doc.add_paragraph()
    r1 = p1.add_run("活动内容：")
    set_run(r1, bold=True)
    r2 = p1.add_run(act)
    set_run(r2)
    p1.paragraph_format.left_indent = Pt(21)
    p1.paragraph_format.space_after = Pt(2)
    # 设计意图
    p2 = doc.add_paragraph()
    r3 = p2.add_run("设计意图：")
    set_run(r3, bold=True)
    r4 = p2.add_run(intent)
    set_run(r4)
    p2.paragraph_format.left_indent = Pt(21)
    p2.paragraph_format.space_after = Pt(4)

para("时间合计：3′+8′+5′+6′+8′+10′+3′+2′ = 45 分钟（其中学生口头输出环节合计约 23 分钟，占课堂时间一半以上，凸显口语训练重点）。", size=10.5, indent=21)

# ===== 八、板书设计 =====
heading("八、板书设计")
p = para("Unit 6  I'm going to study computer science", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
board = doc.add_table(rows=3, cols=2)
board.style = "Table Grid"
board.alignment = WD_TABLE_ALIGNMENT.CENTER
b_left = board.cell(0, 0).paragraphs[0]
r = b_left.add_run("新词汇")
set_run(r, bold=True)
board.cell(1, 0).paragraphs[0].add_run("computer programmer  engineer\npilot  scientist  doctor  actor")
board.cell(2, 0).paragraphs[0].add_run("途径：study … really hard /\ntake … lessons / practice … every day")
b_r0 = board.cell(0, 1).paragraphs[0]
r = b_r0.add_run("核心句型")
set_run(r, bold=True)
board.cell(1, 1).paragraphs[0].add_run("What are you going to be when you grow up?\nI'm going to be a(n) …")
board.cell(2, 1).paragraphs[0].add_run("How are you going to do that?\nI'm going to …")
for c in board.columns[0].cells:
    c.width = Cm(7.6)
for c in board.columns[1].cells:
    c.width = Cm(8.6)

# ===== 九、口语训练专项设计说明 =====
heading("九、口语训练专项设计说明（本课重点）")
bullet("① 开口机会全员覆盖：", "通过 chain drill（人人接龙）、pair work（两两操练）、4 人组轮换采访，保证每位学生课内开口不少于 5 次。")
bullet("② 阶梯式口语任务链：", "机械操练（准确）→ 听后模仿（地道）→ 情境 role play（半开放）→ 自由采访汇报（开放输出），梯度递进，层层加码。")
bullet("③ 充分的语言支架：", "句型卡、职业/途径图卡、采访记录单和追问提示词（Why? When? What's your first step?）降低表达难度，让中下水平学生也能成句成段开口。")
bullet("④ 评价促进表达：", "采用“三星互评表”（内容★ 语音★ 流利度★）与“最佳记者/最佳应答者”评选，以评促说，激发持续开口动机。")
bullet("⑤ 课后口语延伸：", "必做录音作业将口头输出延伸到课外，形成“课内练—课外用”的闭环。")

# ===== 十、教学反思（预设栏） =====
heading("十、教学反思（课后填写）")
para("① 学生开口参与面与流利度是否达到预期？哪个口语环节参与度最高？", indent=21)
para("② 句型支架与追问提示是否需要调整？学困生是否获得足够支持？", indent=21)
para("③ 下节课需要巩固的语音语调与句型问题：", indent=21)

doc.save("/workspace/outputs/英语教案.docx")
print("saved")
