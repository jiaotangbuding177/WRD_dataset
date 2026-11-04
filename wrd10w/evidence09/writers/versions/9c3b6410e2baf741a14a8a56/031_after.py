# -*- coding: utf-8 -*-
"""Render all deliverable images: product design sheet, logo, brand guideline, 11 BP pages (16:9)."""
from playwright.sync_api import sync_playwright
import pathlib

OUT = pathlib.Path('/workspace/outputs')

# ---------- shared data ----------
CHARS = [
    ('01', '孙悟空', '齐天大圣', 'sun', '#C8322B', '金箍棒+黄金甲', ['#C8322B', '#D4AF37']),
    ('02', '哪吒', '三坛海会', 'nezha', '#E2582B', '风火轮+混天绫', ['#E2582B', '#D4AF37']),
    ('03', '杨戬', '二郎真君', 'jian', '#8A93A6', '天眼+三尖两刃刀', ['#8A93A6', '#2B3A55']),
    ('04', '白素贞', '西湖白蛇', 'umb', '#5E8B7E', '青伞+水波纹', ['#5E8B7E', '#F5F1E8']),
    ('05', '嫦娥', '广寒宫主', 'moon', '#B7A57A', '飘带+玉兔伴生', ['#B7A57A', '#D4AF37']),
    ('06', '雷震子', '风雷双翅', 'thunder', '#2B3A55', '肉翅+风雷锤', ['#2B3A55', '#D4AF37']),
    ('07', '九尾狐', '青丘之主', 'fox', '#D98B99', '九尾扇形展开', ['#D98B99', '#D4AF37']),
    ('08', '敖丙', '东海龙子', 'pearl', '#3E7C8F', '龙角+珠形底座', ['#3E7C8F', '#9FD3E0']),
]
HIDDEN = ('隐藏', '应龙', '鎏金限定 1/144', 'dragon', '#D4AF37', '全身电镀鎏金+透明水晶底座', ['#D4AF37', '#C8322B'])

RED, GOLD, BLUE, CREAM = '#C8322B', '#D4AF37', '#2B3A55', '#F5F1E8'

CLOUD_PATH = 'M20 62 Q20 36 46 36 Q52 14 74 18 Q96 6 108 30 Q130 26 134 50 Q150 54 146 68 L26 68 Q16 66 20 62 Z'

def cloud(color=GOLD, opacity=0.35, w=140):
    return f'''<svg viewBox="0 0 160 76" width="{w}" style="opacity:{opacity}">
      <path d="{CLOUD_PATH}" fill="{color}"/>
      <circle cx="78" cy="42" r="10" fill="none" stroke="{CREAM}" stroke-width="3"/></svg>'''

def clouds_corner(color=GOLD, op=0.30):
    return f'''<div style="position:absolute;inset:0;pointer-events:none">
      <div style="position:absolute;top:28px;left:36px">{cloud(color,op,150)}</div>
      <div style="position:absolute;top:70px;left:150px">{cloud(color,op*0.7,90)}</div>
      <div style="position:absolute;bottom:28px;right:36px;transform:rotate(180deg)">{cloud(color,op,150)}</div>
      <div style="position:absolute;bottom:70px;right:150px;transform:rotate(180deg)">{cloud(color,op*0.7,90)}</div>
    </div>'''

def wavebar(h=26, color=RED, op=0.9, n=26, w=1920):
    seg = 38
    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {n*seg} {h}" preserveAspectRatio="none" style="display:block;opacity:{op}">
      {''.join(f'<path d="M{i*38} {h} Q{i*38+19} {h-22} {i*38+38} {h} Z" fill="{color}"/>' for i in range(n))}</svg>'''

# ---------- character icons (simple stroke SVG inside a circle) ----------
def icon(name, c=GOLD, c2=RED):
    s = f'stroke="{c}" stroke-width="7" fill="none" stroke-linecap="round"'
    inner = {
      'sun':     f'<line x1="28" y1="112" x2="112" y2="28" {s}/><rect x="20" y="104" width="16" height="16" rx="3" fill="{c2}" transform="rotate(45 28 112)"/><rect x="104" y="20" width="16" height="16" rx="3" fill="{c2}" transform="rotate(45 112 28)"/>',
      'nezha':   f'<circle cx="46" cy="94" r="20" {s}/><circle cx="94" cy="94" r="20" {s}/><path d="M26 70 Q40 34 70 30 M114 70 Q100 34 70 30" {s}/>',
      'jian':    f'<line x1="70" y1="26" x2="70" y2="104" {s}/><path d="M46 40 V64 M94 40 V64 M46 40 L70 26 L94 40" {s}/><circle cx="70" cy="64" r="7" fill="{c2}"/>',
      'umb':     f'<path d="M24 78 A46 46 0 0 1 116 78" {s}/><line x1="24" y1="78" x2="116" y2="78" {s}/><line x1="70" y1="32" x2="70" y2="112" {s}/><path d="M40 52 L46 78 M100 52 L94 78" {s}/>',
      'moon':    f'<path d="M84 26 A44 44 0 1 0 84 106 A34 34 0 1 1 84 26 Z" {s}/><circle cx="46" cy="52" r="12" {s}/><circle cx="40" cy="46" r="2.5" fill="{c}"/><circle cx="50" cy="46" r="2.5" fill="{c}"/>',
      'thunder': f'<polygon points="78,22 52,72 68,72 58,112 96,58 78,58 92,22" fill="{c2}" stroke="none"/><path d="M30 88 Q18 64 34 46 M110 88 Q122 64 106 46" {s}/>',
      'fox':     f'<path d="M70 104 Q30 96 26 60 M70 104 Q24 84 34 48 M70 104 Q28 68 48 40 M70 104 Q40 56 66 36 M70 104 Q56 52 84 36" {s}/><circle cx="86" cy="92" r="14" fill="{c2}" stroke="none"/>',
      'pearl':   f'<circle cx="70" cy="56" r="22" {s}/><path d="M22 96 Q34 82 46 96 T70 96 T94 96 T118 96" {s}/><path d="M52 44 Q60 34 70 44 Q80 54 88 44" {s}/>',
      'dragon':  f'<path d="M28 100 Q30 56 66 40 Q98 28 112 46 Q96 44 88 54 Q104 54 110 68 Q92 62 82 70 Q94 76 94 88 Q76 76 60 82 Q40 88 28 100 Z" fill="{c}" stroke="none"/><circle cx="92" cy="50" r="3" fill="{CREAM}"/>',
    }[name]
    return f'<svg viewBox="0 0 140 140" width="100%" height="100%">{inner}</svg>'

def char_card(no, name, title, ic, main, note, dots, hidden=False):
    bg = f'linear-gradient(150deg,{GOLD},{RED})' if hidden else '#FFFDF6'
    border = f'3px solid {GOLD}' if hidden else f'2px solid {main}44'
    tag = '<div style="position:absolute;top:10px;right:10px;background:%s;color:#fff;font-size:18px;padding:2px 12px;border-radius:12px">隐藏</div>' % RED if hidden else ''
    no_c = GOLD if hidden else main
    return f'''<div style="position:relative;background:{bg};border:{border};border-radius:18px;padding:16px 14px;display:flex;flex-direction:column;align-items:center;box-shadow:0 4px 14px #2b3a5518">
      {tag}
      <div style="color:{no_c};font-weight:900;font-size:20px;letter-spacing:2px">{no}</div>
      <div style="width:110px;height:110px;border-radius:50%;background:{main}18;border:2px solid {main}55;margin:8px 0;padding:12px">{icon(ic, hidden and RED or main, hidden and GOLD or GOLD)}</div>
      <div style="font-family:'Noto Serif CJK SC','Noto Sans CJK SC',serif;font-weight:900;font-size:30px;color:{BLUE}">{name}</div>
      <div style="font-size:17px;color:{RED};font-weight:700;margin:2px 0">{title}</div>
      <div style="font-size:15px;color:#2b3a55aa">{note}</div>
      <div style="display:flex;gap:6px;margin-top:8px">{''.join(f'<span style="width:16px;height:16px;border-radius:50%;background:{d};display:inline-block"></span>' for d in dots)}</div>
    </div>'''

# ---------- page chrome ----------
def footer(page_no, title='潮神纪 MythBox｜国潮神话IP盲盒商业计划书'):
    return f'''<div style="position:absolute;left:0;right:0;bottom:0;display:flex;justify-content:space-between;align-items:flex-end">
      <div style="background:{RED};color:#fff;font-size:20px;padding:8px 34px 10px 60px;border-radius:0 24px 0 0;display:flex;align-items:center;gap:12px">
        <span style="display:inline-block;width:26px;height:26px;border-radius:50%;background:{GOLD};color:{RED};font-weight:900;text-align:center;line-height:26px;font-size:15px">潮</span>{title}
      </div>
      <div style="color:{GOLD};font-weight:900;font-size:26px;padding:0 48px 10px 0">{page_no:02d}</div>
    </div>
    <div style="position:absolute;left:0;right:0;bottom:44px">{wavebar(18, GOLD, 0.35)}</div>'''

def page(title, subtitle, body, no, gold_bar=True):
    bar = f'<div style="width:120px;height:10px;background:{GOLD};border-radius:5px;margin-top:10px"></div>' if gold_bar else ''
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
      *{{margin:0;padding:0;box-sizing:border-box}}
      body{{width:1920px;height:1080px;background:{CREAM};font-family:'Noto Sans CJK SC',sans-serif;color:{BLUE};position:relative;overflow:hidden;
           background-image:radial-gradient(#d4af3712 2px,transparent 2px);background-size:46px 46px}}
    </style></head><body>
    {clouds_corner()}
    <div style="position:absolute;top:52px;left:60px;right:60px">
      <div style="display:flex;align-items:baseline;gap:24px">
        <span style="font-family:'Noto Serif CJK SC','Noto Sans CJK SC',serif;font-size:56px;font-weight:900;color:{RED}">{title}</span>
        <span style="font-size:26px;color:{BLUE}aa">{subtitle}</span>
      </div>{bar}
    </div>
    {body}
    {footer(no)}
    </body></html>'''

# ---------- BP pages ----------
def p1():
    emblem = f'''<div style="width:300px;height:300px;border-radius:50%;background:radial-gradient(circle at 35% 30%,{RED} 0%,#9e2019 100%);border:8px solid {GOLD};box-shadow:0 0 0 6px {CREAM},0 0 0 10px {GOLD}88,0 18px 40px #2b3a5533;margin:0 auto;display:flex;align-items:center;justify-content:center">
        <div style="width:190px">{icon('dragon', GOLD)}</div>
      </div>'''
    body = f'''<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px;padding-bottom:60px">
      {emblem}
      <div style="font-family:'Noto Serif CJK SC','Noto Sans CJK SC',serif;font-size:120px;font-weight:900;letter-spacing:26px;color:{BLUE};text-shadow:4px 4px 0 {GOLD}55">潮神纪</div>
      <div style="font-size:34px;letter-spacing:14px;color:{GOLD};font-weight:700">M Y T H B O X</div>
      <div style="font-size:40px;font-weight:700;color:{RED};letter-spacing:8px;border-top:2px solid {GOLD};border-bottom:2px solid {GOLD};padding:12px 44px">国潮神话IP盲盒创业商业计划书</div>
      <div style="font-size:24px;color:{BLUE}cc;letter-spacing:4px">首系列《封神纪·启》｜8 常规款 + 1 隐藏款</div>
    </div>'''
    return page('', '', body, 1, gold_bar=False)

def p2():
    cards = [
        ('已确认方向', '国潮盲盒 × 神话IP', '在多个创业方向中选定国潮盲盒，进一步聚焦神话IP赛道'),
        ('产品结构', '8 常规款 + 1 隐藏款', '隐藏款概率 1/144，对外公示，合规经营'),
        ('核心差异', '开盒即开典故', '包装与典故卡承载神话科普，收藏即读神话'),
    ]
    ch = ''.join(f'''<div style="background:#FFFDF6;border:2px solid {GOLD};border-radius:20px;padding:34px 30px;flex:1;box-shadow:0 6px 18px #2b3a5514">
        <div style="font-size:26px;color:{GOLD};font-weight:900;letter-spacing:4px">{c[0]}</div>
        <div style="font-size:44px;font-weight:900;color:{RED};margin:14px 0">{c[1]}</div>
        <div style="font-size:23px;line-height:1.6;color:{BLUE}cc">{c[2]}</div>
      </div>''' for c in cards)
    sil = ''.join(f'<div style="width:78px;height:78px;border-radius:50%;background:{RED}14;border:2px solid {GOLD}66;padding:10px">{icon(c[3], BLUE, RED)}</div>' for c in CHARS + [HIDDEN])
    body = f'''<div style="position:absolute;top:190px;left:60px;right:60px;display:flex;gap:56px">
      <div style="writing-mode:vertical-rl;font-family:'Noto Serif CJK SC',serif;font-size:64px;font-weight:900;color:#fff;background:{RED};padding:34px 20px;border-radius:16px;letter-spacing:14px;box-shadow:6px 6px 0 {GOLD}">项目概述</div>
      <div style="flex:1">
        <div style="font-size:40px;font-weight:900;color:{BLUE}">中国神话谱系垂直盲盒品牌 —— <span style="color:{RED}">每个神仙都有故事</span></div>
        <div style="display:flex;gap:28px;margin-top:44px">{ch}</div>
        <div style="display:flex;gap:22px;margin-top:52px;align-items:center;justify-content:center">{sil}</div>
        <div style="text-align:center;font-size:20px;color:{BLUE}88;margin-top:12px">《封神纪·启》九位角色剪影</div>
      </div>
    </div>'''
    return page('项目概述', 'PROJECT OVERVIEW', body, 2)

def p3():
    bars = [40, 55, 68, 82, 100]
    chart = ''.join(f'''<div style="display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:8px">
        <div style="width:96px;height:{h*3.4}px;border-radius:10px 10px 0 0;background:linear-gradient(180deg,{RED},{GOLD})"></div>
        <span style="font-size:19px;color:{BLUE}aa">20{21+i}E</span></div>''' for i, h in enumerate(bars))
    cards = [
        ('核心人群', '18–35岁 Z世代与都市女性，收藏习惯强、复购率高'),
        ('竞争格局', '头部为平台型多IP品牌，垂直文化母题品牌稀缺'),
        ('我们的差异化', '文化根基深 ＋ 无海外IP授权费 ＋ 谱系化长线上新'),
    ]
    rc = ''.join(f'''<div style="background:#FFFDF6;border-left:8px solid {RED};border-radius:12px;padding:20px 26px;margin-bottom:22px;box-shadow:0 4px 12px #2b3a5510">
        <div style="font-size:27px;font-weight:900;color:{RED}">{t}</div><div style="font-size:22px;color:{BLUE}cc;margin-top:6px;line-height:1.5">{d}</div></div>''' for t, d in cards)
    body = f'''<div style="position:absolute;top:190px;left:60px;right:60px;display:flex;gap:60px">
      <div style="flex:1.1;background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:36px 30px 26px">
        <div style="font-size:26px;font-weight:900;color:{BLUE}">潮玩市场持续增长（示意）</div>
        <div style="font-size:21px;color:{RED};margin:6px 0 20px">两位数年增速 · 盲盒为潮玩第一大品类</div>
        <div style="display:flex;gap:34px;align-items:flex-end;height:400px">{chart}</div>
      </div>
      <div style="flex:1">{rc}</div>
    </div>'''
    return page('市场分析', 'MARKET ANALYSIS', body, 3)

def p4():
    grid = ''.join(char_card(*c) for c in CHARS)
    hid = char_card(*HIDDEN, hidden=True)
    body = f'''<div style="position:absolute;top:180px;left:60px;right:60px">
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:24px">{grid}{hid}</div>
      <div style="margin-top:26px;background:{BLUE};color:{CREAM};border-radius:14px;padding:14px 30px;font-size:22px;display:flex;justify-content:space-around">
        <span>单只规格：高 8–10cm</span><span>材质：PVC / ABS ＋ 局部树脂件</span><span>隐藏款：电镀鎏金 ＋ 透明水晶底座</span><span>建议零售 ¥69/盒</span>
      </div>
    </div>'''
    return page('产品方案', '《封神纪·启》8+1 选品', body, 4)

def p5():
    # packaging box mockup
    sil_cells = ''.join(f'<div style="width:52px;height:52px;border-radius:50%;background:{CREAM}22;border:1px solid {GOLD}88;display:flex;align-items:center;justify-content:center">{icon(c[2], CREAM, GOLD)}</div>' for c in CHARS)
    box = f'''<div style="display:flex;align-items:flex-end;gap:0">
      <div style="width:120px;height:400px;background:linear-gradient(180deg,#a82820,{RED});transform:skewY(-14deg) translateX(14px);border-radius:8px 0 0 0;border:2px solid {GOLD}"></div>
      <div style="width:330px;height:420px;background:linear-gradient(160deg,{RED},#8f1f18);border:3px solid {GOLD};border-radius:0 10px 10px 0;padding:22px;box-shadow:14px 18px 30px #2b3a5533">
        <div style="color:{GOLD};font-family:'Noto Serif CJK SC',serif;font-size:40px;font-weight:900;letter-spacing:6px">封神纪·启</div>
        <div style="color:{CREAM};font-size:16px;letter-spacing:4px;margin:4px 0 16px">潮神纪 MythBox 盲盒系列</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;width:170px">{sil_cells}<div style="border:2px dashed {GOLD};border-radius:50%;color:{GOLD};display:flex;align-items:center;justify-content:center;font-size:30px;font-weight:900">？</div></div>
        <div style="color:{GOLD};font-size:15px;margin-top:18px;letter-spacing:2px">隐藏款概率公示 1/144 · 内含角色典故卡</div>
      </div>
    </div>'''
    # story card front/back
    front = f'''<div style="width:300px;height:430px;background:#FFFDF6;border:3px solid {GOLD};border-radius:18px;padding:20px;text-align:center;box-shadow:10px 12px 24px #2b3a5522">
        <div style="color:{RED};font-weight:900;font-size:18px;letter-spacing:3px">封神纪·启 典故卡</div>
        <div style="width:180px;height:180px;margin:16px auto;border-radius:50%;background:{RED}14;border:2px solid {RED}55;padding:16px">{icon('sun', RED, GOLD)}</div>
        <div style="font-family:'Noto Serif CJK SC',serif;font-size:36px;font-weight:900;color:{BLUE}">孙悟空</div>
        <div style="color:{GOLD};font-size:18px;font-weight:700;margin-top:4px">齐天大圣</div>
      </div>'''
    back = f'''<div style="width:300px;height:430px;background:{BLUE};border:3px solid {GOLD};border-radius:18px;padding:22px;color:{CREAM};box-shadow:10px 12px 24px #2b3a5522">
        <div style="color:{GOLD};font-weight:900;font-size:19px;letter-spacing:3px;border-bottom:1px solid {GOLD}77;padding-bottom:8px">神话典故</div>
        <p style="font-size:20px;line-height:1.8;margin-top:14px">石猴出世，学艺方寸山；龙宫得金箍棒，大闹天宫；后护唐僧西行，终成斗战胜佛。</p>
        <div style="margin-top:18px;color:{GOLD};font-size:16px">收集图鉴</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:8px">{''.join(f'<div style="height:34px;border:1px solid {GOLD}88;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:15px;color:{GOLD}">{c[1][:2]}</div>' for c in CHARS)}<div style="height:34px;border:1px dashed {GOLD};border-radius:6px;display:flex;align-items:center;justify-content:center;color:{GOLD};font-weight:900">?</div></div>
      </div>'''
    hid_card = f'''<div style="width:300px;height:430px;background:linear-gradient(160deg,{GOLD},#b8912a);border:3px solid {RED};border-radius:18px;padding:22px;text-align:center;box-shadow:10px 12px 24px #2b3a5533">
        <div style="color:{RED};font-weight:900;font-size:19px;letter-spacing:3px">隐藏款 · 典藏编号卡</div>
        <div style="width:180px;height:180px;margin:16px auto;border-radius:50%;background:{CREAM}33;border:2px solid {CREAM};padding:14px">{icon('dragon', RED, GOLD)}</div>
        <div style="font-family:'Noto Serif CJK SC',serif;font-size:36px;font-weight:900;color:{RED}">应龙</div>
        <div style="color:{CREAM};font-size:18px;margin-top:4px">鎏金限定 · No.____ /144</div>
        <div style="margin-top:14px;font-size:15px;color:{RED}dd">透明水晶底座 · 电镀鎏金工艺</div>
      </div>'''
    body = f'''<div style="position:absolute;top:186px;left:60px;right:60px;display:flex;gap:54px;align-items:flex-start">
      <div>{box}<div style="text-align:center;font-size:21px;color:{BLUE}aa;margin-top:22px">天地盖盲盒包装：主视觉＋8款剪影＋「？」隐藏格</div></div>
      <div style="display:flex;gap:26px"><div>{front}<div style="text-align:center;font-size:19px;color:{BLUE}aa;margin-top:14px">典故卡正面</div></div><div>{back}<div style="text-align:center;font-size:19px;color:{BLUE}aa;margin-top:14px">典故卡背面</div></div><div>{hid_card}<div style="text-align:center;font-size:19px;color:{BLUE}aa;margin-top:14px">隐藏款编号卡</div></div></div>
    </div>
    <div style="position:absolute;right:66px;top:150px;background:{RED};color:{CREAM};font-size:22px;padding:10px 24px;border-radius:24px">集齐 8 款 → 兑换「封神谱·典藏册」</div>'''
    return page('产品设计', '包装与卡片', body, 5)

def p6():
    sw = [('#C8322B', '朱砂红 主色'), ('#D4AF37', '鎏金 辅色'), ('#2B3A55', '黛蓝 辅色'), ('#F5F1E8', '月白 底色')]
    swatches = ''.join(f'''<div style="flex:1;text-align:center">
        <div style="height:120px;border-radius:16px;background:{c};border:2px solid #2b3a5522"></div>
        <div style="font-size:22px;font-weight:900;margin-top:10px">{n}</div><div style="font-size:19px;color:{BLUE}aa">{c}</div></div>''' for c, n in sw)
    pats = [(cloud(GOLD, .9, 120), '祥云纹'), (wavebar(60, RED, .8, 7, 260), '水波纹'),
            (f'<svg width="120" height="60"><polygon points="10,10 40,10 30,30 50,30 20,58 30,34 8,34" fill="{BLUE}"/></svg>', '雷纹')]
    pat_html = ''.join(f'''<div style="flex:1;background:#FFFDF6;border:2px solid {GOLD}77;border-radius:14px;padding:16px;text-align:center">
        <div style="height:70px;display:flex;align-items:center;justify-content:center">{s}</div>
        <div style="font-size:20px;color:{BLUE};margin-top:8px">{n}</div></div>''' for s, n in pats)
    body = f'''<div style="position:absolute;top:180px;left:60px;right:60px;display:flex;gap:50px">
      <div style="width:560px;display:flex;flex-direction:column;gap:26px">
        <div style="background:#FFFDF6;border:2px solid {GOLD};border-radius:20px;padding:30px;display:flex;align-items:center;gap:26px">
          <div style="width:150px;height:150px;border-radius:50%;background:{RED};border:6px solid {GOLD};display:flex;align-items:center;justify-content:center;padding:18px">{icon('dragon', GOLD)}</div>
          <div><div style="font-family:'Noto Serif CJK SC',serif;font-size:58px;font-weight:900;color:{BLUE};letter-spacing:8px">潮神纪</div>
          <div style="color:{GOLD};font-size:22px;letter-spacing:6px">MYTHBOX</div>
          <div style="font-size:17px;color:{BLUE}88;margin-top:6px">组合标：图形徽章 ＋ 中文字标（已确认方向一＋方向三组合）</div></div>
        </div>
        <div style="background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:24px 28px">
          <div style="font-size:22px;font-weight:900;color:{RED}">字体规范</div>
          <div style="font-family:'Noto Serif CJK SC',serif;font-size:30px;font-weight:900;margin-top:8px">标题：书法 / 宋体系（思源宋体）</div>
          <div style="font-size:24px;margin-top:6px">正文：黑体系（思源黑体）</div>
        </div>
        <div style="background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:20px 28px">
          <div style="font-size:22px;font-weight:900;color:{RED}">应用示例</div>
          <div style="display:flex;gap:14px;margin-top:12px;font-size:19px">
            <span style="background:{RED};color:{CREAM};padding:10px 18px;border-radius:10px">盲盒包装</span>
            <span style="background:{BLUE};color:{CREAM};padding:10px 18px;border-radius:10px">角色卡片</span>
            <span style="background:{GOLD};color:{BLUE};padding:10px 18px;border-radius:10px">社媒头像 / 横幅</span>
          </div>
        </div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:26px">
        <div style="display:flex;gap:20px">{swatches}</div>
        <div style="display:flex;gap:20px">{pat_html}</div>
        <div style="background:{BLUE};color:{CREAM};border-radius:16px;padding:18px 26px;font-size:20px;line-height:1.6">
          使用规则：主色用于包装主视觉与标题；鎏金仅作描边与点睛；辅助底纹使用比例不超过版面 20%。
        </div>
      </div>
    </div>'''
    return page('品牌视觉', 'BRAND VISUAL IDENTITY', body, 6)

def p7():
    ch = [('抽盒机小程序', '复购主场 · 在线抽取'), ('天猫 / 抖音直播', '端盒连抽 · 内容带货'), ('线下快闪 / 集合店', '体验触点 · 寄售点位')]
    chh = ''.join(f'''<div style="flex:1;background:#FFFDF6;border-top:10px solid {GOLD};border-radius:14px;padding:24px;text-align:center;box-shadow:0 4px 14px #2b3a5510">
        <div style="font-size:27px;font-weight:900;color:{BLUE}">{t}</div><div style="font-size:20px;color:{RED};margin-top:8px">{d}</div></div>''' for t, d in ch)
    fly = [('开盒', RED), ('晒单', GOLD), ('集卡', RED), ('社群', BLUE), ('复购', RED)]
    flyh = ''.join(f'''<div style="display:flex;align-items:center;gap:10px">
        <div style="width:96px;height:96px;border-radius:50%;background:{c};color:{CREAM};display:flex;align-items:center;justify-content:center;font-size:26px;font-weight:900;box-shadow:0 6px 14px #2b3a5522">{t}</div>
        {'<span style="font-size:30px;color:'+GOLD+'">→</span>' if i < 4 else ''}</div>''' for i, (t, c) in enumerate(fly))
    body = f'''<div style="position:absolute;top:186px;left:60px;right:60px;display:flex;gap:56px">
      <div style="flex:1.15;display:flex;flex-direction:column;gap:30px">
        <div style="background:linear-gradient(140deg,{RED},#8f1f18);border:3px solid {GOLD};border-radius:22px;color:{CREAM};padding:30px 36px;display:flex;align-items:center;gap:34px">
          <div style="font-size:88px;font-weight:900;color:{GOLD}">¥69</div>
          <div style="font-size:24px;line-height:1.7">单盒建议零售价<br>端盒 8 只 ¥552（约8折激励）<br>隐藏款不单售 · 仅抽取获得</div>
        </div>
        <div style="display:flex;gap:22px">{chh}</div>
      </div>
      <div style="flex:1;background:#FFFDF6;border:2px solid {GOLD}88;border-radius:22px;padding:34px">
        <div style="font-size:26px;font-weight:900;color:{RED}">私域增长飞轮</div>
        <div style="display:flex;flex-wrap:wrap;gap:18px;margin-top:30px;align-items:center">{flyh}</div>
        <div style="margin-top:34px;font-size:21px;color:{BLUE}cc;line-height:1.7">晒隐藏款返现、集卡进度 H5 分享、会员积分兑换典藏册，驱动高复购与自传播。</div>
      </div>
    </div>'''
    return page('商业模式与定价', 'BUSINESS MODEL', body, 7)

def p8():
    cost = [('材料（PVC/ABS/树脂+电镀摊销）', 10), ('开模摊销（9套模具/系列）', 6), ('加工·组装·涂装人工', 7), ('包装盒+卡片+内衬', 3.5), ('质检+仓储物流', 2.5)]
    total = sum(v for _, v in cost)
    colors = [RED, GOLD, BLUE, '#8A93A6', '#3E7C8F']
    segs = ''.join(f'<div style="width:{v/total*100:.1f}%;background:{c};height:100%;display:flex;align-items:center;justify-content:center;color:{CREAM};font-size:19px;font-weight:700">{v}元</div>' for (l, v), c in zip(cost, colors))
    legend = ''.join(f'<div style="display:flex;align-items:center;gap:10px;margin:10px 0"><span style="width:18px;height:18px;border-radius:4px;background:{c};display:inline-block"></span><span style="font-size:21px">{l}：{v}元</span></div>' for (l, v), c in zip(cost, colors))
    steps = [('零售价', '¥69', BLUE), ('渠道让利 35–40%', '−¥24~28', '#8A93A6'), ('出厂净收', '¥41–45', GOLD), ('单盒毛利', '约30–45%', RED)]
    wf = ''.join(f'''<div style="flex:1;text-align:center">
        <div style="height:{110 if i%2==0 else 84}px;margin:0 8px;border-radius:12px;background:{c};color:{CREAM};display:flex;flex-direction:column;align-items:center;justify-content:center">
          <div style="font-size:20px;opacity:.9">{t}</div><div style="font-size:30px;font-weight:900">{v}</div></div></div>''' for i, (t, v, c) in enumerate(steps))
    body = f'''<div style="position:absolute;top:190px;left:60px;right:60px;display:flex;gap:56px">
      <div style="flex:1.1;background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:34px">
        <div style="font-size:26px;font-weight:900;color:{BLUE}">单盒完全成本：约 ¥25–33（按10万只/系列）</div>
        <div style="display:flex;height:96px;border-radius:12px;overflow:hidden;margin:26px 0 20px">{segs}</div>
        {legend}
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:26px">
        <div style="background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:30px">
          <div style="font-size:26px;font-weight:900;color:{RED};margin-bottom:24px">毛利瀑布</div>
          <div style="display:flex;align-items:flex-end">{wf}</div>
        </div>
        <div style="background:{BLUE};color:{CREAM};border-radius:16px;padding:20px 28px;font-size:22px">直营 / 自营抽盒机渠道省去经销环节，毛利率更高。</div>
      </div>
    </div>'''
    return page('成本结构与毛利', 'COST & MARGIN', body, 8)

def p9():
    steps = [
        ('① 制造', '广东东莞/深圳潮玩代工厂', 'PVC搪胶＋ABS注塑＋树脂件，具备电镀工艺；初筛3家，小批量5000只试产验证'),
        ('② 包装印刷', '精选彩印厂', '天地盖盒＋专色烫金（隐藏款卡），打样色差 ΔE≤3'),
        ('③ 品控', '驻厂QC＋三方抽检', '跌落 / 色差 / 涂装 AQL 2.5；返修金5%约束'),
    ]
    st = ''.join(f'''<div style="flex:1;background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:30px;position:relative">
        <div style="position:absolute;top:-20px;left:26px;background:{RED};color:{CREAM};font-size:24px;font-weight:900;padding:6px 22px;border-radius:20px">{t}</div>
        <div style="font-size:26px;font-weight:900;color:{BLUE};margin-top:16px">{a}</div>
        <div style="font-size:21px;color:{BLUE}cc;line-height:1.7;margin-top:12px">{b}</div></div>''' for t, a, b in steps)
    arrows = '<div style="text-align:center;font-size:44px;color:'+GOLD+'">▶</div>'
    body = f'''<div style="position:absolute;top:200px;left:60px;right:60px;display:flex;align-items:stretch;gap:14px">{st[0:1][0]}{arrows}{st[1:2][0]}{arrows}{st[2:3][0]}</div>
    <div style="position:absolute;left:60px;right:60px;top:560px;background:{BLUE};color:{CREAM};border-radius:18px;padding:26px 36px;display:flex;justify-content:space-around;font-size:23px">
      <span><b style="color:{GOLD}">结算节奏</b></span><span>模具费 3 : 4 : 3 分期</span><span>量产货款月结 30 天</span><span>预留返修金 5%</span>
    </div>'''.replace('{st[0:1][0]}', '')
    # fix: build explicitly
    body = f'''<div style="position:absolute;top:200px;left:60px;right:60px;display:flex;align-items:stretch;gap:14px">
      <div style="flex:1;background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:30px;position:relative">
        <div style="position:absolute;top:-20px;left:26px;background:{RED};color:{CREAM};font-size:24px;font-weight:900;padding:6px 22px;border-radius:20px">① 制造</div>
        <div style="font-size:26px;font-weight:900;color:{BLUE};margin-top:16px">广东东莞 / 深圳潮玩代工厂</div>
        <div style="font-size:21px;color:{BLUE}cc;line-height:1.7;margin-top:12px">PVC搪胶＋ABS注塑＋树脂件，具备电镀工艺；初筛3家，小批量5000只试产验证。</div></div>
      <div style="display:flex;align-items:center;font-size:44px;color:{GOLD}">▶</div>
      <div style="flex:1;background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:30px;position:relative">
        <div style="position:absolute;top:-20px;left:26px;background:{RED};color:{CREAM};font-size:24px;font-weight:900;padding:6px 22px;border-radius:20px">② 包装印刷</div>
        <div style="font-size:26px;font-weight:900;color:{BLUE};margin-top:16px">精选彩印厂</div>
        <div style="font-size:21px;color:{BLUE}cc;line-height:1.7;margin-top:12px">天地盖盒＋专色烫金（隐藏款卡），打样确认色差 ΔE≤3。</div></div>
      <div style="display:flex;align-items:center;font-size:44px;color:{GOLD}">▶</div>
      <div style="flex:1;background:#FFFDF6;border:2px solid {GOLD}88;border-radius:20px;padding:30px;position:relative">
        <div style="position:absolute;top:-20px;left:26px;background:{RED};color:{CREAM};font-size:24px;font-weight:900;padding:6px 22px;border-radius:20px">③ 品控</div>
        <div style="font-size:26px;font-weight:900;color:{BLUE};margin-top:16px">驻厂QC＋三方抽检</div>
        <div style="font-size:21px;color:{BLUE}cc;line-height:1.7;margin-top:12px">跌落 / 色差 / 涂装 AQL 2.5；返修金5%约束。</div></div>
    </div>
    <div style="position:absolute;left:60px;right:60px;top:600px;background:{BLUE};color:{CREAM};border-radius:18px;padding:26px 36px;display:flex;justify-content:space-around;font-size:23px">
      <span><b style="color:{GOLD}">结算节奏</b></span><span>模具费 3 : 4 : 3 分期</span><span>量产货款月结 30 天</span><span>预留返修金 5%</span>
    </div>'''
    return page('供应链对接', 'SUPPLY CHAIN', body, 9)

def p10():
    tl = [('预热期 T-30', '剪影悬念海报逐日放出，话题 #谁会封神#'), ('发布期 T-7', '全员官图＋典故短视频，KOC 测评'), ('首发期 T0', '抽盒机小程序＋天猫抖音＋线下快闪同步'), ('续销期 T+30', '晒单返现·集卡兑换典藏册·季度预告')]
    tlh = ''.join(f'''<div style="position:relative;padding:0 0 34px 44px">
        <div style="position:absolute;left:8px;top:6px;width:20px;height:20px;border-radius:50%;background:{RED};border:4px solid {GOLD}"></div>
        {'<div style="position:absolute;left:16px;top:30px;bottom:-6px;width:4px;background:'+GOLD+'55"></div>' if i < 3 else ''}
        <div style="font-size:25px;font-weight:900;color:{RED}">{t}</div>
        <div style="font-size:21px;color:{BLUE}cc;margin-top:4px">{d}</div></div>''' for i, (t, d) in enumerate(tl))
    ms = ['首发6个月售出10万只', '私域会员 5 万人', '季度上新·神话谱系多系列', '博物馆 / 汉服品牌跨界联名']
    msh = ''.join(f'''<div style="background:{'linear-gradient(140deg,'+RED+',#8f1f18)' if i==0 else '#FFFDF6'};border:2px solid {GOLD}88;border-radius:16px;padding:20px 22px;margin-bottom:16px;font-size:22px;font-weight:700;color:{CREAM if i==0 else BLUE};display:flex;gap:14px;align-items:center">
        <span style="color:{GOLD};font-size:26px">▲</span>{m}</div>''' for i, m in enumerate(ms))
    budget = [('达人种草投放', 40, RED), ('快闪店与物料', 25, GOLD), ('私域运营', 15, BLUE), ('公关话题', 12, '#8A93A6'), ('机动预留', 8, '#3E7C8F')]
    bh = ''.join(f'''<div style="flex:{v};background:{c};display:flex;align-items:center;justify-content:center;color:{CREAM};font-size:19px;font-weight:700">{t} {v}%</div>''' for t, v, c in budget)
    body = f'''<div style="position:absolute;top:186px;left:60px;right:60px;display:flex;gap:56px">
      <div style="flex:1">{tlh}</div>
      <div style="flex:1">{msh}</div>
    </div>
    <div style="position:absolute;left:60px;right:60px;top:812px">
      <div style="font-size:21px;color:{BLUE}aa;margin-bottom:8px">首发季预算分配（提案）</div>
      <div style="display:flex;height:52px;border-radius:12px;overflow:hidden">{bh}</div>
    </div>'''
    return page('营销策略与发展规划', 'MARKETING & ROADMAP', body, 10)

def p11():
    body = f'''<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:30px;padding-bottom:60px">
      <div style="width:220px;height:220px;border-radius:50%;background:{RED};border:6px solid {GOLD};display:flex;align-items:center;justify-content:center;padding:34px">{icon('dragon', GOLD)}</div>
      <div style="font-family:'Noto Serif CJK SC',serif;font-size:96px;font-weight:900;letter-spacing:18px;color:{BLUE};text-shadow:3px 3px 0 {GOLD}55">诚邀共启封神纪</div>
      <div style="font-size:34px;color:{RED};letter-spacing:6px">让每一个中国神话，都住进一只盲盒</div>
      <div style="width:420px;height:2px;background:{GOLD}"></div>
      <div style="font-size:24px;color:{BLUE}aa;letter-spacing:3px">潮神纪 MythBox｜商务合作 · 敬请垂询</div>
    </div>'''
    return page('', '', body, 11, gold_bar=False)

# ---------- standalone sheets ----------
def product_sheet():
    row = ''.join(f'''<div style="width:170px;text-align:center">
      <div style="width:150px;height:150px;border-radius:50%;background:#FFFDF6;border:3px solid {c[4]};margin:0 auto;padding:20px;box-shadow:0 6px 14px #2b3a5518">{icon(c[2], c[4], GOLD)}</div>
      <div style="font-size:24px;font-weight:900;color:{BLUE};margin-top:10px">{c[1]}</div>
      <div style="font-size:17px;color:{c[4]};font-weight:700">{c[3]}</div>
      <div style="font-size:15px;color:#2b3a55aa">{c[5]}</div>
    </div>''' for c in CHARS)
    hid = f'''<div style="width:230px;text-align:center">
      <div style="width:200px;height:200px;border-radius:50%;background:radial-gradient(circle at 32% 28%,{GOLD},#a87f1c);border:4px solid {RED};margin:0 auto;padding:26px;box-shadow:0 10px 26px #d4af3766">{icon('dragon', RED, GOLD)}</div>
      <div style="font-size:30px;font-weight:900;color:{RED};margin-top:10px">应龙</div>
      <div style="font-size:19px;color:{GOLD};font-weight:900">鎏金限定 · 隐藏款 1/144</div>
      <div style="font-size:15px;color:#2b3a55aa">电镀鎏金＋透明水晶底座</div>
    </div>'''
    # mini box + card at bottom
    boxm = f'''<div style="width:300px;height:250px;background:linear-gradient(160deg,{RED},#8f1f18);border:3px solid {GOLD};border-radius:10px;padding:16px;box-shadow:10px 12px 26px #2b3a5533">
      <div style="color:{GOLD};font-family:'Noto Serif CJK SC',serif;font-size:28px;font-weight:900">封神纪·启</div>
      <div style="color:{CREAM};font-size:13px;letter-spacing:2px">潮神纪 MythBox 盲盒 · 天地盖彩盒</div>
      <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:10px">{''.join(f'<div style="aspect-ratio:1;border-radius:50%;background:{CREAM}22;border:1px solid {GOLD}88"></div>' for _ in range(8))}<div style="aspect-ratio:1;border:1px dashed {GOLD};border-radius:50%;color:{GOLD};display:flex;align-items:center;justify-content:center;font-weight:900">?</div></div>
      <div style="color:{GOLD};font-size:12px;margin-top:10px">正面：系列主视觉＋8款剪影＋？隐藏格</div>
    </div>'''
    cardm = f'''<div style="width:230px;height:250px;background:#FFFDF6;border:3px solid {GOLD};border-radius:14px;padding:14px;text-align:center;box-shadow:8px 10px 20px #2b3a5522">
      <div style="color:{RED};font-weight:900;font-size:14px">角色典故卡</div>
      <div style="width:110px;height:110px;margin:10px auto;border-radius:50%;background:{RED}12;border:2px solid {RED}55;padding:10px">{icon('sun', RED, GOLD)}</div>
      <div style="font-size:24px;font-weight:900;color:{BLUE}">孙悟空</div>
      <div style="font-size:14px;color:{GOLD};font-weight:700">正面：立绘＋名称｜背面：60字典故＋收集图鉴格</div>
    </div>'''
    hidm = f'''<div style="width:230px;height:250px;background:linear-gradient(160deg,{GOLD},#b8912a);border:3px solid {RED};border-radius:14px;padding:14px;text-align:center;box-shadow:8px 10px 20px #2b3a5533">
      <div style="color:{RED};font-weight:900;font-size:14px">隐藏款典藏编号卡</div>
      <div style="width:110px;height:110px;margin:10px auto;border-radius:50%;background:{CREAM}33;border:2px solid {CREAM};padding:10px">{icon('dragon', RED, GOLD)}</div>
      <div style="font-size:24px;font-weight:900;color:{RED}">应龙 No.__/144</div>
      <div style="font-size:13px;color:{RED}dd">鎏金卡面 · 附典藏编号</div>
    </div>'''
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0;box-sizing:border-box}}
      body{{width:1920px;height:1080px;background:{CREAM};font-family:'Noto Sans CJK SC',sans-serif;color:{BLUE};position:relative;overflow:hidden;
      background-image:radial-gradient(#d4af3712 2px,transparent 2px);background-size:46px 46px}}</style></head><body>
      {clouds_corner()}
      <div style="text-align:center;padding-top:34px">
        <span style="font-family:'Noto Serif CJK SC',serif;font-size:50px;font-weight:900;color:{RED};letter-spacing:8px">《封神纪·启》盲盒产品设计图</span>
        <div style="font-size:22px;color:{BLUE}aa;margin-top:8px">8 常规款 ＋ 1 隐藏款（含包装盒与角色卡片）｜潮神纪 MythBox</div>
      </div>
      <div style="display:flex;justify-content:center;align-items:flex-end;gap:26px;margin-top:36px;padding:0 60px">
        {row}{hid}
      </div>
      <div style="display:flex;justify-content:center;gap:46px;margin-top:44px">{boxm}{cardm}{hidm}
        <div style="width:420px;background:{BLUE};color:{CREAM};border-radius:14px;padding:20px 26px;font-size:18px;line-height:1.8">
          <b style="color:{GOLD}">设计说明</b><br>· 单只高 8–10cm，PVC/ABS＋树脂件<br>· 隐藏款概率 1/144，公示合规<br>· 集齐 8 款兑换「封神谱·典藏册」<br>· 配色：朱砂红 / 鎏金 / 黛蓝 / 月白
        </div>
      </div>
      <div style="position:absolute;left:0;right:0;bottom:0">{wavebar(22, RED, .85)}</div>
    </body></html>'''
    return html, (1920, 1080)

def logo_sheet():
    W, H = 1600, 1200
    mark = f'''<div style="width:340px;height:340px;border-radius:50%;background:radial-gradient(circle at 35% 30%,{RED},#9e2019);border:10px solid {GOLD};box-shadow:0 0 0 8px {CREAM},0 0 0 14px {GOLD}88,0 20px 44px #2b3a5533;display:flex;align-items:center;justify-content:center;padding:60px">{icon('dragon', GOLD)}</div>'''
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0;box-sizing:border-box}}
      body{{width:{W}px;height:{H}px;background:{CREAM};font-family:'Noto Sans CJK SC',sans-serif;color:{BLUE};display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}}</style></head><body>
      {clouds_corner(GOLD, .35)}
      <div style="display:flex;align-items:center;gap:60px">
        {mark}
        <div>
          <div style="font-family:'Noto Serif CJK SC',serif;font-size:150px;font-weight:900;letter-spacing:22px;color:{BLUE};text-shadow:5px 5px 0 {GOLD}55">潮神纪</div>
          <div style="font-size:44px;letter-spacing:16px;color:{GOLD};font-weight:700;margin-top:14px">MYTHBOX</div>
          <div style="width:520px;height:4px;background:{GOLD};margin:26px 0 18px"></div>
          <div style="font-size:26px;color:{BLUE}aa;letter-spacing:4px">国潮神话IP盲盒 · 品牌标志（图形徽章＋中文字标组合）</div>
        </div>
      </div>
      <div style="position:absolute;bottom:44px;left:0;right:0;text-align:center;font-size:20px;color:{BLUE}77">组合式Logo：方向一（图形徽章）＋ 方向三（字标）· 已确认组合方向</div>
    </body></html>'''
    return html, (W, H)

def guideline_sheet():
    sw = [('#C8322B', '朱砂红 主色'), ('#D4AF37', '鎏金 辅色'), ('#2B3A55', '黛蓝 辅色'), ('#F5F1E8', '月白 底色')]
    swatches = ''.join(f'''<div style="flex:1;text-align:center">
      <div style="height:110px;border-radius:14px;background:{c};border:2px solid #2b3a5522"></div>
      <div style="font-size:21px;font-weight:900;margin-top:8px">{n}</div><div style="font-size:17px;color:{BLUE}aa">{c}</div></div>''' for c, n in sw)
    pats = [(cloud(GOLD, .9, 120), '祥云纹'), (wavebar(56, RED, .85, 7, 240), '水波纹'),
            (f'<svg width="110" height="56"><polygon points="10,10 40,10 30,30 50,30 20,54 30,32 8,32" fill="{BLUE}"/></svg>', '雷纹')]
    pat_html = ''.join(f'''<div style="flex:1;background:#FFFDF6;border:2px solid {GOLD}77;border-radius:12px;padding:14px;text-align:center">
      <div style="height:64px;display:flex;align-items:center;justify-content:center">{s}</div>
      <div style="font-size:19px;margin-top:6px">{n}</div></div>''' for s, n in pats)
    html = f'''<!doctype html><html><head><meta charset="utf-8"><style>*{{margin:0;padding:0;box-sizing:border-box}}
      body{{width:1920px;height:1080px;background:{CREAM};font-family:'Noto Sans CJK SC',sans-serif;color:{BLUE};position:relative;overflow:hidden}}</style></head><body>
      <div style="text-align:center;padding-top:26px">
        <span style="font-family:'Noto Serif CJK SC',serif;font-size:44px;font-weight:900;color:{RED};letter-spacing:6px">潮神纪 MythBox · 全套品牌视觉规范</span>
      </div>
      <div style="display:flex;gap:34px;padding:26px 60px 0">
        <div style="width:480px;display:flex;flex-direction:column;gap:20px">
          <div style="background:#FFFDF6;border:2px solid {GOLD};border-radius:16px;padding:22px;display:flex;align-items:center;gap:20px">
            <div style="width:120px;height:120px;border-radius:50%;background:{RED};border:5px solid {GOLD};display:flex;align-items:center;justify-content:center;padding:14px">{icon('dragon', GOLD)}</div>
            <div><div style="font-family:'Noto Serif CJK SC',serif;font-size:44px;font-weight:900;letter-spacing:6px">潮神纪</div>
            <div style="color:{GOLD};font-size:18px;letter-spacing:5px">MYTHBOX</div></div>
          </div>
          <div style="background:#FFFDF6;border:2px solid {GOLD}88;border-radius:16px;padding:16px 22px;font-size:18px;line-height:1.7">
            <b style="color:{RED}">Logo组合</b>：横版组合标 / 竖版组合标 / 单图形标<br>安全间距＝徽章直径的 1/4；最小使用宽度 24mm。
          </div>
          <div style="background:#FFFDF6;border:2px solid {GOLD}88;border-radius:16px;padding:16px 22px;font-size:19px">
            <b style="color:{RED}">字体规范</b><br>
            <span style="font-family:'Noto Serif CJK SC',serif;font-weight:900;font-size:24px">标题：书法 / 宋体系（思源宋体）</span><br>
            <span style="font-size:21px">正文：黑体系（思源黑体）</span>
          </div>
          <div style="background:{BLUE};color:{CREAM};border-radius:16px;padding:14px 22px;font-size:17px;line-height:1.7">应用：包装主视觉 / 角色卡片 / 社媒头像横幅 / 快闪店物料</div>
        </div>
        <div style="flex:1;display:flex;flex-direction:column;gap:22px">
          <div><div style="font-size:21px;font-weight:900;color:{RED};margin-bottom:10px">品牌色板</div><div style="display:flex;gap:18px">{swatches}</div></div>
          <div><div style="font-size:21px;font-weight:900;color:{RED};margin-bottom:10px">辅助图形</div><div style="display:flex;gap:16px">{pat_html}</div></div>
          <div style="background:#FFFDF6;border:2px solid {GOLD}88;border-radius:16px;padding:16px 24px;font-size:18px;line-height:1.7">
            <b style="color:{RED}">使用规则</b>：主色用于主视觉与标题；鎏金仅作描边与点睛，不用于大面积铺色；辅助底纹占比≤20%；月白为默认背景，保证对比度。
          </div>
        </div>
      </div>
      <div style="position:absolute;left:0;right:0;bottom:0">{wavebar(20, GOLD, .4)}</div>
    </body></html>'''
    return html, (1920, 1080)

# ---------- render ----------
def main():
    jobs = {}
    for i, fn in enumerate([p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11], 1):
        jobs[f'bp_P{i:02d}.png'] = (fn(), (1920, 1080))
    jobs['03_产品设计图.png'] = product_sheet()
    jobs['04_品牌Logo.png'] = logo_sheet()
    jobs['05_品牌视觉规范.png'] = guideline_sheet()
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        for name, (html, (w, h)) in jobs.items():
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.set_content(html, wait_until='networkidle')
            pg.screenshot(path=str(OUT / name))
            pg.close()
            print('done', name)
        b.close()

if __name__ == '__main__':
    main()
