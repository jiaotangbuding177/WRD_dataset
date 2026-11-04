# -*- coding: utf-8 -*-
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

FONT = "Noto Sans CJK SC"

def set_font(run, size, bold=False, color=RGBColor(0x33,0x33,0x33)):
    f = run.font
    f.size = Pt(size); f.bold = bold; f.color.rgb = color; f.name = FONT
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn('a:ea'))
    if ea is None:
        ea = rPr.makeelement(qn('a:ea'), {}); rPr.append(ea)
    ea.set('typeface', FONT)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
slide = prs.slides.add_slide(prs.slide_layouts[6])

# background
bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = RGBColor(0xF7,0xF9,0xFC); bg.line.fill.background()
bg.shadow.inherit = False

# title
tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.28), Inches(12.33), Inches(0.8))
tf = tb.text_frame; tf.word_wrap = True
p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
r = p.add_run(); r.text = "核心场景"; set_font(r, 34, True, RGBColor(0x1F,0x4E,0x79))

scenarios = [
    ("场景一：成果评估", RGBColor(0x2E,0x75,0xB6), [
        "导入模板/接口上传，校验解析入库",
        "智能体引擎：检索·归证·研判·评分·报告",
        "实时展示进度，按分/置信度/风险筛选候选",
    ]),
    ("场景二：AI评分辅助评审", RGBColor(0x00,0x8B,0x8B), [
        "同时查看申报材料与智能体建议、证据、风险",
        "专家独立评分，可调建议分并填差异说明",
        "预评、评分、意见全程留痕，供复核审计",
    ]),
    ("场景三：项目跟进与管理", RGBColor(0xC0,0x5B,0x11), [
        "“我的项目”工作台，查看授权项目与阶段",
        "更新进展、上传成果、记录里程碑",
        "滞后自动预警；无权修改专家最终评分",
    ]),
    ("场景四：全局监控与预警", RGBColor(0x70,0x30,0xA0), [
        "全局看板按区域/领域/阶段汇总状态",
        "阈值标记滞后，可催办并下钻查看详情",
        "过程监督与异常协调，不改评审分数",
    ]),
]

x0, y0 = Inches(0.5), Inches(1.25)
w, h = Inches(6.1), Inches(2.85)
gx, gy = Inches(0.15), Inches(0.2)
for i, (title, color, items) in enumerate(scenarios):
    x = x0 + (w + gx) * (i % 2)
    y = y0 + (h + gy) * (i // 2)
    card = slide.shapes.add_shape(1, x, y, w, h)  # rounded rect -> use MSO_SHAPE.ROUNDED_RECTANGLE
    card.fill.solid(); card.fill.fore_color.rgb = RGBColor(0xFF,0xFF,0xFF)
    card.line.color.rgb = color; card.line.width = Pt(1.25)
    card.shadow.inherit = False
    try:
        from pptx.enum.shapes import MSO_SHAPE
        # replace with rounded rect: easier to just keep rect
        pass
    except Exception:
        pass
    # header bar
    hdr = slide.shapes.add_shape(1, x, y, w, Inches(0.55))
    hdr.fill.solid(); hdr.fill.fore_color.rgb = color; hdr.line.fill.background()
    hdr.shadow.inherit = False
    htf = hdr.text_frame; htf.margin_left = Inches(0.15); htf.margin_right = Inches(0.05)
    htf.margin_top = Inches(0.02); htf.margin_bottom = Inches(0.02)
    htf.vertical_anchor = MSO_ANCHOR.MIDDLE
    hp = htf.paragraphs[0]
    hr = hp.add_run(); hr.text = title; set_font(hr, 17, True, RGBColor(0xFF,0xFF,0xFF))
    # body
    btb = slide.shapes.add_textbox(x + Inches(0.18), y + Inches(0.62), w - Inches(0.36), h - Inches(0.72))
    btf = btb.text_frame; btf.word_wrap = True
    for j, it in enumerate(items):
        bp = btf.paragraphs[0] if j == 0 else btf.add_paragraph()
        bp.space_after = Pt(6)
        br = bp.add_run(); br.text = "• " + it; set_font(br, 13)

out = "/workspace/outputs/核心场景一页PPT.pptx"
prs.save(out)
print(out)
