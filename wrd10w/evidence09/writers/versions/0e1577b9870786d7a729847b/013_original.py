#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""攻防箭小游戏宣传动画 - 8镜头代码动画渲染器
中间项目保留在本目录, 修改 SCENE_DUR / 各场景函数后重跑即可重渲染.
"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

W, H = 1280, 720
SS = 2                      # 超采样抗锯齿
FPS = 24
SCENE_DUR = [5, 10, 5, 15, 10, 10, 5, 8]   # 分镜脚本时长(秒), 总68s
TOTAL = sum(SCENE_DUR)
OUT_FRAMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_fonts = {}
def F(size):
    size = int(size)
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT_PATH, size)
    return _fonts[size]

# ---------- 调色板 ----------
RED    = (255, 77, 94)
RED_D  = (200, 40, 60)
BLUE   = (63, 169, 245)
BLUE_D = (30, 110, 190)
SKIN   = (255, 214, 170)
DARK   = (45, 45, 65)
WHITE  = (255, 255, 255)
YELLOW = (255, 205, 60)
GREEN  = (110, 200, 110)
GREEN_D= (80, 165, 85)
GRAY   = (160, 160, 170)

def ease(t):        # ease-in-out
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)
def lerp(a, b, k):
    return a + (b - a) * k

def base_canvas(sky_top=(150, 210, 255), sky_bot=(210, 240, 255)):
    img = Image.new("RGB", (W * SS, H * SS), sky_top)
    d = ImageDraw.Draw(img)
    for i in range(H * SS):
        k = i / (H * SS)
        c = tuple(int(lerp(sky_top[j], sky_bot[j], k)) for j in range(3))
        d.line([(0, i), (W * SS, i)], fill=c)
    return img, d

def downscale(img):
    return img.resize((W, H), Image.LANCZOS)

def text(d, xy, s, size, fill=WHITE, anchor="mm", stroke=DARK, sw=None):
    sw = sw if sw is not None else max(2, int(size / 15))
    d.text(xy, s, font=F(size), fill=fill, anchor=anchor,
           stroke_width=sw, stroke_fill=stroke)

def wrap(s, size, maxw):
    f = F(size)
    lines, cur = [], ""
    for ch in s:
        if d_len(f, cur + ch) > maxw and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur: lines.append(cur)
    return lines

def d_len(f, s):
    return f.getlength(s)

def subtitle(d, s):
    """底部旁白字幕条"""
    size = 34 * SS // 2 * 2 // 2 * 2  # ~34*SS/2 → keep simple below
    size = 36
    lines = wrap(s, size, int(W * 0.82))
    lh = size + 14
    bh = lh * len(lines) + 26
    y0 = H - bh - 18
    d.rounded_rectangle([int(W*0.05)*SS//SS, 0, 0, 0]) if False else None
    x0, x1 = int(W * 0.06), int(W * 0.94)
    d.rounded_rectangle([x0, y0, x1, y0 + bh], radius=18,
                        fill=(20, 20, 35), outline=(255, 255, 255), width=3)
    ty = y0 + 13 + lh // 2
    for ln in lines:
        text(d, (W // 2, ty), ln, size, fill=WHITE)
        ty += lh

def scene_title(d, s, size=64, y=110, color=YELLOW):
    text(d, (W // 2, y), s, size, fill=color, sw=int(size / 12))

# ---------- Q版角色 ----------
def draw_player(d, x, y, s, team, facing=1, pose="stand", t=0.0, ghost=False):
    """(x, y)=脚底中心; s=缩放(1.0约110px高); team='red'/'blue'"""
    body = team == "red" and RED or BLUE
    body_d = team == "red" and RED_D or BLUE_D
    if ghost:
        body, body_d = GRAY, (120, 120, 130)
    bob = math.sin(t * 6) * 3 * s if pose == "stand" else 0
    jump = 0
    if pose == "cheer":
        jump = -abs(math.sin(t * 7)) * 16 * s
    x, y = x, y + bob + jump

    if pose == "down":
        # 出局: 坐地
        d.ellipse([x - 26*s, y - 14*s, x + 26*s, y + 14*s], fill=body)      # 身体(倒)
        d.ellipse([x + 10*s, y - 46*s, x + 48*s, y - 8*s], fill=SKIN)      # 头偏一侧
        d.rounded_rectangle([x + 12*s, y - 38*s, x + 44*s, y - 26*s], radius=6*s, fill=DARK)  # 面罩
        for i in range(3):  # 晕圈星星
            a = t * 4 + i * 2.09
            sx, sy = x + 29*s + math.cos(a) * 26*s, y - 62*s + math.sin(a) * 8*s
            star(d, sx, sy, 7*s, YELLOW)
        return

    lean = 0.18 if pose == "run" else 0.0
    hx = x + lean * 20 * s * facing
    hip_y = y - 34 * s
    head_cy = y - 78 * s

    # 腿
    if pose == "run":
        ph = math.sin(t * 14)
        for k, sgn in ((0, 1), (1, -1)):
            d.line([hx - 8*s + k*8*s, hip_y, hx + sgn * ph * 16 * s, y], fill=body_d, width=int(7*s))
    elif pose == "dodge":
        d.line([x - 12*s, hip_y, x - 16*s, y], fill=body_d, width=int(7*s))
        d.line([x + 12*s, hip_y, x + 18*s, y], fill=body_d, width=int(7*s))
    else:
        d.line([x - 8*s, hip_y, x - 10*s, y], fill=body_d, width=int(7*s))
        d.line([x + 8*s, hip_y, x + 10*s, y], fill=body_d, width=int(7*s))
    for fx, fy in ((x-10*s, y), (x+10*s, y)):
        d.ellipse([fx-5*s, fy-4*s, fx+5*s, fy+4*s], fill=DARK)

    # 身体
    d.rounded_rectangle([x - 17*s, y - 62*s, x + 17*s, y - 26*s], radius=12*s, fill=body)
    # 号码带
    d.ellipse([x - 7*s, y - 52*s, x + 7*s, y - 38*s], fill=WHITE)

    # 手臂+弓
    bow_shown = pose in ("shoot", "aim", "draw")
    if pose == "cheer":
        sw_ = math.sin(t * 7) * 4
        d.line([x - 14*s, y - 56*s, x - 24*s, y - 80*s - sw_*s], fill=body_d, width=int(6*s))
        d.line([x + 14*s, y - 56*s, x + 24*s, y - 80*s + sw_*s], fill=body_d, width=int(6*s))
    elif bow_shown:
        ax_ = x + 26 * s * facing
        d.line([x, y - 50*s, ax_, y - 52*s], fill=body_d, width=int(6*s))       # 前臂持弓
        pull = 14 * s if pose == "draw" else 4 * s
        d.line([x, y - 50*s, x - pull * facing, y - 48*s], fill=body_d, width=int(6*s))  # 后臂拉弦
        draw_bow(d, ax_, y - 52*s, s, facing, pulled=(pose == "draw"))
    elif pose == "catch":
        d.line([x - 12*s, y - 54*s, x + 20*s*facing, y - 58*s], fill=body_d, width=int(6*s))
        d.line([x + 12*s, y - 54*s, x + 26*s*facing, y - 50*s], fill=body_d, width=int(6*s))
    elif pose == "run":
        ph = math.sin(t * 14)
        d.line([x - 12*s, y - 54*s, x - 20*s, y - 40*s + ph*10*s], fill=body_d, width=int(6*s))
        d.line([x + 12*s, y - 54*s, x + 20*s, y - 40*s - ph*10*s], fill=body_d, width=int(6*s))
    else:
        d.line([x - 14*s, y - 50*s, x - 18*s, y - 30*s], fill=body_d, width=int(6*s))
        d.line([x + 14*s, y - 50*s, x + 18*s, y - 30*s], fill=body_d, width=int(6*s))

    # 头
    d.ellipse([hx - 22*s, head_cy - 22*s, hx + 22*s, head_cy + 22*s], fill=SKIN)
    d.pieslice([hx - 22*s, head_cy - 22*s, hx + 22*s, head_cy + 22*s], 180, 360, fill=body_d)  # 头发/帽
    # 面罩
    d.rounded_rectangle([hx - 20*s, head_cy - 10*s, hx + 20*s, head_cy + 4*s], radius=8*s, fill=DARK)
    d.line([hx - 14*s, head_cy - 3*s, hx + 14*s, head_cy - 3*s], fill=(110, 200, 255), width=int(3*s))

def draw_bow(d, x, y, s, facing, pulled=False):
    col = (140, 90, 50)
    box = [x - 10*s, y - 26*s, x + 10*s, y + 26*s]
    if facing < 0:
        box = [x - 10*s, y - 26*s, x + 10*s, y + 26*s]
    d.arc(box, start=90 if facing > 0 else -90, end=270 if facing > 0 else 90, fill=col, width=int(4*s))
    sx = x - 2*s*facing
    pull_x = sx - 14*s if pulled else sx
    d.line([sx, y - 25*s, pull_x, y], fill=(230, 230, 230), width=int(2*s))
    d.line([sx, y + 25*s, pull_x, y], fill=(230, 230, 230), width=int(2*s))
    if pulled:
        arrow(d, pull_x - 16*s*facing, y, pull_x + 14*s*facing, y, 0.7*s)

def arrow(d, x0, y0, x1, y1, s=1.0, col=DARK):
    d.line([x0, y0, x1, y1], fill=col, width=max(2, int(3*s)))
    ang = math.atan2(y1 - y0, x1 - x0)
    L = 9 * s
    d.polygon([(x1 + math.cos(ang)*L, y1 + math.sin(ang)*L),
               (x1 + math.cos(ang+2.5)*L*.7, y1 + math.sin(ang+2.5)*L*.7),
               (x1 + math.cos(ang-2.5)*L*.7, y1 + math.sin(ang-2.5)*L*.7)], fill=YELLOW)  # 泡沫头
    for sgn in (-2.6, 2.6):
        d.polygon([(x0, y0),
                   (x0 + math.cos(ang+sgn)*7*s, y0 + math.sin(ang+sgn)*7*s),
                   (x0 + math.cos(ang)*5*s, y0 + math.sin(ang)*5*s)], fill=RED)

def star(d, cx, cy, r, col=YELLOW):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = -math.pi/2 + i * math.pi/5
        pts.append((cx + rr*math.cos(a), cy + rr*math.sin(a)))
    d.polygon(pts, fill=col)

def flash_ring(d, cx, cy, k, col=WHITE, rmax=90):
    r = 12 + k * rmax
    w = max(2, int((1 - k) * 10))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=w)

def burst(d, cx, cy, k, col=YELLOW):
    """命中爆炸星芒"""
    r = 20 + k * 46
    for i in range(8):
        a = i * math.pi / 4 + k
        x1, y1 = cx + r*math.cos(a), cy + r*math.sin(a)
        x0, y0 = cx + r*0.45*math.cos(a), cy + r*0.45*math.sin(a)
        d.line([x0, y0, x1, y1], fill=col, width=max(3, int(8*(1-k))))
    star(d, cx, cy, 18*(1-k) + 6, col)

def dust(d, x, y, t, col=(225, 225, 225)):
    for i in range(3):
        ph = (t * 2 + i * 0.5) % 1
        r = 6 + ph * 12
        d.ellipse([x - r, y - r - ph*14, x + r, y + r - ph*14],
                  outline=col, width=2)

def confetti(d, t, n=40, seed=7, ytop=0):
    rnd = random.Random(seed)
    cols = [RED, BLUE, YELLOW, GREEN, (255, 150, 220)]
    for i in range(n):
        px = rnd.uniform(0, W)
        spd = rnd.uniform(90, 220)
        py = (ytop + rnd.uniform(0, H) + t * spd) % (H * 1.1) - H * 0.05
        a = t * 5 + i
        sz = rnd.uniform(4, 9)
        d.polygon([(px + math.cos(a)*sz, py), (px, py + math.sin(a)*sz),
                   (px - math.cos(a)*sz, py), (px, py - math.sin(a)*sz)],
                  fill=cols[i % len(cols)])

def ground(d, y=560):
    d.rectangle([0, y*SS//1, 0, 0]) if False else None
    d.rectangle([0, y, W*SS, y + 40], fill=GREEN)
    d.rectangle([0, y + 40, W*SS, H*SS], fill=GREEN_D)

def obstacle(d, cx, cy, w, h, col=(255, 170, 60)):
    d.rounded_rectangle([cx - w/2, cy - h/2, cx + w/2, cy + h/2], radius=int(h/4), fill=col)
    d.rounded_rectangle([cx - w/2 + 6, cy - h/2 + 8, cx + w/2 - 6, cy - h/2 + h*0.35],
                        radius=10, fill=(255, 210, 130))

def target(d, cx, cy, r, rings=(WHITE, RED, WHITE, RED)):
    for i, c in enumerate(rings):
        rr = r * (1 - i * 0.22)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=c, outline=DARK, width=2)
    d.ellipse([cx - r*0.16, cy - r*0.16, cx + r*0.16, cy + r*0.16], fill=YELLOW)

def cloud(d, cx, cy, s=1.0):
    for ox, oy, r in ((-30, 8, 20), (0, 0, 28), (32, 8, 20)):
        d.ellipse([(cx+ox*s)*SS-r*s*SS, (cy+oy*s)*SS-r*s*SS, (cx+ox*s)*SS+r*s*SS, (cy+oy*s)*SS+r*s*SS], fill=WHITE)

# ============================================================
# 场景函数: 每帧调用, t 为镜头内秒数, T 为镜头时长
# ============================================================

def scene1(t, T):
    """开场标题: 场景拉远→拉弦特写→箭飞出, 标题弹出"""
    img, d = base_canvas()
    for cx in (180, 640, 1080):
        cloud(d, cx, 110 + (cx % 3) * 30, 1.2)
    ground(d, 560)
    # 中线与场地
    d.line([W // 2, 560, W // 2, H * SS], fill=WHITE, width=6)
    k = ease(t / T)
    # 两队小人 (世界坐标)
    for i, xx in enumerate((300, 420, 540)):
        draw_player(d, xx, 640, 1.15, "red", facing=1, pose="stand", t=t + i)
    for i, xx in enumerate((740, 860, 980)):
        draw_player(d, xx, 640, 1.15, "blue", facing=-1, pose="stand", t=t + i)
    # 前景拉弦弓箭手 (世界坐标 660, 690 大号)
    if t < T * 0.62:
        draw_player(d, 640, 700, 2.2, "red", facing=1, pose="draw", t=t)
    else:
        draw_player(d, 640, 700, 2.2, "red", facing=1, pose="shoot", t=t)
        # 箭飞出
        ak = ease((t - T * 0.62) / (T * 0.38))
        ax = 700 + ak * 900
        for tr in range(5):
            arrow(d, ax - 60 - tr*46, 640 - tr*4, ax - 20 - tr*46, 640 - tr*4, 1.2, col=(200, 200, 210))
        arrow(d, ax - 60, 640, ax, 640, 1.4)
        if ak < 0.35:
            flash_ring(d, 700, 640, ak / 0.35)

    # 拉近镜头裁切
    cw = lerp(W, W * 0.42, k) * SS
    ch = lerp(H, H * 0.42, k) * SS
    fcx = lerp(W * SS / 2, 640 * SS, k)
    fcy = lerp(H * SS * 0.55, 600 * SS, k)
    x0 = max(0, min(W * SS - cw, fcx - cw / 2))
    y0 = max(0, min(H * SS - ch, fcy - ch / 2))
    frame = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
    df = ImageDraw.Draw(frame)
    # 标题弹出
    ts_ = t / T
    if ts_ > 0.12:
        pop = min(1.0, (ts_ - 0.12) / 0.18)
        sz = 92 * (0.6 + 0.4 * ease(pop))
        text(df, (W // 2, 150), "攻防箭小游戏", sz, fill=YELLOW, sw=10)
        if pop >= 1 and ts_ < 0.8:
            text(df, (W // 2, 240), "Archery Dodgeball Battle", 30, fill=WHITE, sw=4)
    subtitle(df, "来一场刺激的攻防对战吧！攻防箭——融合射箭与闪避球的团队大战！")
    return frame

def scene2(t, T):
    """规则介绍: 俯视场地 → 装备展示"""
    phase = ease(t / (T * 0.5))
    if t < T * 0.52:
        img = Image.new("RGB", (W, H), (250, 247, 238))
        d = ImageDraw.Draw(img)
        # 俯视场地
        fx0, fy0, fx1, fy1 = 120, 130, 1160, 560
        d.rounded_rectangle([fx0, fy0, fx1, fy1], radius=30, fill=(120, 200, 120), outline=DARK, width=5)
        d.rectangle([fx0 + (fx1-fx0)*0.36, fy0, fx0 + (fx1-fx0)*0.64, fy1], fill=(255, 235, 150))  # 安全区
        d.rectangle([fx0 + (fx1-fx0)*0.36, fy0, fx0 + (fx1-fx0)*0.64, fy1], outline=(230, 180, 60), width=4)
        d.line([(fx0+fx1)/2, fy0, (fx0+fx1)/2, fy1], fill=WHITE, width=5)
        # 左红右蓝晕染
        d.rectangle([fx0, fy0, fx0 + (fx1-fx0)*0.36, fy1], fill=(255, 120, 130))
        d.rectangle([fx0 + (fx1-fx0)*0.36, fy0, fx0 + (fx1-fx0)*0.64, fy1], fill=(255, 235, 150))
        d.rectangle([fx0 + (fx1-fx0)*0.64, fy0, fx1, fy1], fill=(110, 190, 255))
        d.line([(fx0+fx1)/2, fy0, (fx0+fx1)/2, fy1], fill=WHITE, width=6)
        text(d, ((fx0 + (fx1-fx0)*0.18), fy0 + 60), "红队区", 44, fill=WHITE, stroke=RED_D)
        text(d, ((fx0 + (fx1-fx0)*0.5), fy0 + 60), "安全中立区", 34, fill=DARK, stroke=WHITE)
        text(d, ((fx0 + (fx1-fx0)*0.82), fy0 + 60), "蓝队区", 44, fill=WHITE, stroke=BLUE_D)
        # 障碍物
        for ox, oy, ow, oh in ((0.12, 0.45, 130, 46), (0.22, 0.78, 110, 42), (0.78, 0.45, 130, 46), (0.88, 0.78, 110, 42)):
            cx, cy = fx0 + (fx1-fx0)*ox, fy0 + (fy1-fy0)*oy
            d.rounded_rectangle([cx-ow/2, cy-oh/2, cx+ow/2, cy+oh/2], radius=20, fill=(255, 170, 60), outline=DARK, width=3)
        text(d, (fx0 + (fx1-fx0)*0.12, fy0 + (fy1-fy0)*0.45), "障碍", 24, fill=DARK, stroke=WHITE)
        text(d, (fx0 + (fx1-fx0)*0.88, fy0 + (fy1-fy0)*0.45), "障碍", 24, fill=DARK, stroke=WHITE)
        # 箭靶
        for i in range(3):
            tx = fx0 + (fx1-fx0)*0.07
            ty = fy0 + (fy1-fy0)*(0.25 + i*0.25)
            target(d, tx, ty, 26)
            target(d, fx1 - (fx1-fx0)*0.07, ty, 26)
        text(d, (fx0 + (fx1-fx0)*0.07, fy1 - 30), "箭靶", 24, fill=WHITE, stroke=RED_D)
        text(d, (fx1 - (fx1-fx0)*0.07, fy1 - 30), "箭靶", 24, fill=WHITE, stroke=BLUE_D)
        # 顶视图例小人
        for i in range(5):
            px = fx0 + 200 + i * 60
            d.ellipse([px-18, fy0 + (fy1-fy0)*0.62 - 18, px+18, fy0 + (fy1-fy0)*0.62 + 18], fill=RED, outline=WHITE, width=3)
            d.ellipse([px-18, fy0 + (fy1-fy0)*0.42 - 18, px+18, fy0 + (fy1-fy0)*0.42 + 18], fill=BLUE, outline=WHITE, width=3)
        scene_title(d, "场地与装备", 56, 70)
        subtitle(d, "场地分成两半，中间是安全区。每个人有弓和安全泡沫箭，被射中就出局，但接住箭可以复活队友！")
        return downscale(img) if False else img.resize((W, H), Image.LANCZOS) if False else img
    else:
        img, d = base_canvas()
        ground(d, 520)
        tt = (t - T * 0.52) / (T * 0.48)
        # 三件装备卡片
        cards = [("反曲弓+泡沫箭", "弓"), ("防护面罩", "罩"), ("护臂", "臂")]
        cw_, ch_ = 300, 330
        for i, (label, _) in enumerate(cards):
            cx = 240 + i * 400
            pop = ease(min(1.0, max(0.0, (tt - i * 0.18) / 0.3)))
            yy = 200 + (1 - pop) * 60
            d.rounded_rectangle([cx - cw_//2, yy, cx + cw_//2, yy + ch_], radius=26,
                                fill=WHITE, outline=DARK, width=5)
            bx, by = cx, yy + 120
            if i == 0:
                d.arc([bx - 34, by - 90, bx + 34, by + 90], 90, 270, fill=(140, 90, 50), width=10)
                d.line([bx - 2, by - 88, bx - 2, by + 88], fill=(230, 230, 230), width=4)
                arrow(d, bx - 90, by, bx + 60, by, 1.2)
            elif i == 1:
                d.rounded_rectangle([bx - 80, by - 70, bx + 80, by + 30], radius=34, fill=DARK)
                d.line([bx - 60, by - 14, bx + 60, by - 14], fill=(110, 200, 255), width=8)
                d.rectangle([bx - 50, by + 30, bx + 50, by + 46], fill=(90, 90, 110))
            else:
                d.rounded_rectangle([bx - 70, by - 50, bx + 70, by + 50], radius=26, fill=RED)
                d.rounded_rectangle([bx - 56, by - 38, bx + 56, by - 8], radius=14, fill=(255, 150, 160))
                d.line([bx - 90, by, bx - 70, by], fill=(90, 90, 110), width=10)
            text(d, (cx, yy + ch_ - 60), label, 34, fill=DARK, stroke=WHITE, sw=4)
        text(d, (W // 2, 90), "安全装备", 56, fill=YELLOW, sw=8)
        subtitle(d, "场地分成两半，中间是安全区。每个人有弓和安全泡沫箭，被射中就出局，但接住箭可以复活队友！")
        return downscale(img)

def scene3(t, T):
    """开局冲刺: 两队冲向中立区抢箭再回撤"""
    img, d = base_canvas()
    for cx in (250, 900):
        cloud(d, cx, 100, 1.1)
    ground(d, 560)
    d.line([W // 2, 560, W // 2, H * SS], fill=WHITE, width=6)
    d.ellipse([W//2 - 70, 640, W//2 + 70, 700], fill=(240, 240, 245), outline=DARK, width=4)  # 中间箭堆
    for i in range(4):
        a = i * math.pi / 2 + 0.4
        arrow(d, W//2 + 30*math.cos(a), 660 + 18*math.sin(a), W//2 + 55*math.cos(a), 660 + 24*math.sin(a), 0.9)
    k = math.sin(min(1.0, t / T) * math.pi)   # 0→1→0 冲过去再回来
    shake = math.sin(t * 40) * 3 * (0.4 + k)
    sx = shake
    for i, off in enumerate((-90, -30, 30)):
        xr = W//2 - 460 + k * 380 + off * (1 - k * 0.7)
        xb = W//2 + 460 - k * 380 - off * (1 - k * 0.7)
        draw_player(d, xr + sx, 640 - i * 6, 1.05, "red", facing=1, pose="run", t=t + i * 0.3)
        draw_player(d, xb + sx, 640 - i * 6, 1.05, "blue", facing=-1, pose="run", t=t + i * 0.3)
        dust(d, xr - 30, 655, t * 3 + i)
        dust(d, xb + 30, 655, t * 3 + i + 0.4)
    # 速度线
    for i in range(8):
        yy = 470 + i * 26
        ln = 60 + (i % 3) * 40
        xx = (t * 900 + i * 210) % (W + 200) - 100
        d.line([xx, yy, xx + ln, yy], fill=(255, 255, 255), width=4)
    scene_title(d, "比赛开始！", 56, 90)
    subtitle(d, "比赛开始！大家冲到中间抢箭，然后回到自己的攻击区开始对战！")
    return downscale(img)

def scene4(t, T):
    """激烈攻防: 射箭/闪避/接箭复活/出局"""
    img, d = base_canvas()
    ground(d, 560)
    obstacle(d, 380, 520, 170, 130)
    obstacle(d, 940, 520, 150, 110)
    events = [
        (0.05, 0.30, "shot_r"),     # 红射蓝(被接)
        (0.32, 0.30, "catch"),
        (0.48, 0.24, "revive"),
        (0.62, 0.30, "shot_b"),     # 蓝射红(命中)
        (0.78, 0.30, "out"),
    ]
    red = dict(x=300, y=640, pose="shoot")
    blue = dict(x=1040, y=640, pose="stand")
    gray_blue = dict(x=1130, y=655, pose="stand")
    # 阶段姿态
    if t < 1.0:  red["pose"] = "draw"
    shot_r_t = events[0][0] * T
    catch_t = events[1][0] * T
    revive_t = events[2][0] * T
    shot_b_t = events[3][0] * T
    out_t = events[4][0] * T

    arrowA = None
    if shot_r_t <= t < catch_t:
        k = ease((t - shot_r_t) / (catch_t - shot_r_t))
        arrowA = (lerp(360, 1010, k), lerp(560, 590, k))
    if catch_t <= t < catch_t + 0.5:
        blue["pose"] = "catch"
        flash_ring(d, 1030, 570, (t - catch_t) / 0.5, col=(120, 255, 160))
    elif t >= catch_t:
        blue["pose"] = "shoot" if shot_b_t > t else "stand"
    if shot_r_t <= t < catch_t and arrowA:
        blue["pose"] = "dodge" if (t - shot_r_t) / (catch_t - shot_r_t) > 0.5 else "stand"
        if blue["pose"] == "dodge":
            blue["y"] = 655
    # 复活
    if t >= revive_t:
        k = ease(min(1.0, (t - revive_t) / 0.6))
        draw_player(d, gray_blue["x"], gray_blue["y"], 1.0, "blue", facing=-1, pose="stand", t=t, ghost=(k < 1))
        if k < 1:
            flash_ring(d, gray_blue["x"], gray_blue["y"] - 50, k, col=(255, 230, 120), rmax=120)
            star(d, gray_blue["x"], gray_blue["y"] - 90, 14 + 10 * math.sin(t * 10), YELLOW)
        else:
            star(d, gray_blue["x"], gray_blue["y"] - 100, 12 + 4 * math.sin(t * 8), YELLOW)
        if t < revive_t + 1.2:
            pop = min(1.0, (t - revive_t) / 0.25)
            text(d, (gray_blue["x"], gray_blue["y"] - 150), "复活！", 46 * (0.5 + 0.5 * pop), fill=(120, 255, 160), sw=7)
    else:
        draw_player(d, gray_blue["x"], gray_blue["y"], 1.0, "blue", facing=-1, pose="stand", t=t, ghost=True)
        text(d, (gray_blue["x"], gray_blue["y"] - 120), "出局中", 26, fill=GRAY, sw=4)

    # 蓝队反击箭
    arrowB = None
    if shot_b_t <= t < out_t:
        k = ease((t - shot_b_t) / (out_t - shot_b_t))
        arrowB = (lerp(1010, 360, k), lerp(580, 560, k))
    if t >= out_t:
        red["pose"] = "down"
        if t < out_t + 0.9:
            k = (t - out_t) / 0.5
            if k < 1:
                burst(d, 330, 560, k, col=RED)
                text(d, (330, 480), "出局！", 52 * (0.5 + 0.5 * min(1, k*2)), fill=RED, sw=8)

    draw_player(d, red["x"], red["y"], 1.1, "red", facing=1, pose=red["pose"], t=t)
    draw_player(d, blue["x"], blue["y"], 1.1, "blue", facing=-1, pose=blue["pose"], t=t)
    if arrowA:
        arrow(d, arrowA[0] - 46, arrowA[1], arrowA[0], arrowA[1], 1.2)
    if arrowB:
        arrow(d, arrowB[0] + 46, arrowB[1], arrowB[0], arrowB[1], 1.2)

    # 提示文字
    if t < 1.2:
        text(d, (W//2, 130), "激烈攻防！", 54, fill=YELLOW, sw=8)
    elif revive_t <= t < revive_t + 1.4:
        text(d, (W//2, 130), "接住飞箭 = 复活队友！", 44, fill=(120, 255, 160), sw=7)
    elif t >= out_t + 0.4:
        text(d, (W//2, 130), "被击中就出局！", 44, fill=RED, sw=7)
    subtitle(d, "躲！射！接箭复活！利用掩体走位，团队配合最重要！")
    return downscale(img)

def scene5(t, T):
    """攻击箭靶: 三箭依次命中"""
    img, d = base_canvas()
    ground(d, 560)
    hits = [2.2, 5.0, 7.8]
    txs = [980, 1080, 980]
    tys = [430, 500, 570]
    fallen = 0
    for i, ht in enumerate(hits):
        alive = t < ht
        if alive:
            target(d, txs[i], tys[i], 40)
        else:
            fallen += 1
            k = min(1.0, (t - ht) / 0.5)
            # 倒下的靶
            ang = k * 80
            r = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
            dr = ImageDraw.Draw(r)
            for j, c in enumerate((WHITE, RED, WHITE, RED)):
                rr = 40 * (1 - j * 0.22)
                dr.ellipse([110 - rr, 110 - rr, 110 + rr, 110 + rr], fill=c, outline=DARK, width=2)
            dr.ellipse([110 - 7, 110 - 7, 110 + 7, 110 + 7], fill=YELLOW)
            r = r.rotate(ang, center=(110, 160), expand=False)
            img.paste(r, (int(txs[i]*SS - 110), int(tys[i]*SS - 40)), r)
            if k < 1:
                burst(d, txs[i], tys[i], k, col=YELLOW)
                text(d, (txs[i], tys[i] - 80), "命中！", 44, fill=YELLOW, sw=7)
        # 飞行中的箭
        prev = hits[i-1] if i > 0 else 0.6
        if prev <= t < ht:
            k = ease((t - prev) / (ht - prev))
            ax = lerp(240, txs[i], k); ay = lerp(560, tys[i], k) - math.sin(k * math.pi) * 60
            arrow(d, ax - 46, ay + 6, ax, ay, 1.2)
    # 射手
    pose = "draw" if any(prev <= t < ht for prev, ht in zip([0.6]+hits[:-1] if False else [0.6, 2.2, 5.0], hits)) and False else None
    shooting = any(0.6 <= t < ht for ht in hits) and t < hits[-1]
    idx_shot = sum(1 for ht in hits if t >= ht)
    draw_player(d, 220, 640, 1.15, "red", facing=1, pose="draw" if shooting else "shoot", t=t)
    # 计数
    text(d, (W // 2, 100), f"击落箭靶 {fallen}/3", 52, fill=YELLOW, sw=8)
    subtitle(d, "别忘了攻击对方箭靶！先把所有靶子打掉也能获胜！")
    return downscale(img)

def scene6(t, T):
    """高潮决胜: 慢动作交错箭 + 最后靶被击落 + 胜利"""
    img, d = base_canvas()
    ground(d, 560)
    slow_t = 1.0
    hit_t = 6.2
    # 慢动作暗角
    if slow_t <= t < hit_t:
        d.rectangle([0, 0, W*SS, H*SS], fill=(10, 10, 30))
        vig = Image.new("L", (W, H), 0)
        dv = ImageDraw.Draw(vig)
        dv.ellipse([-200, -140, W + 200, H + 140], fill=255)
        vig = vig.filter(ImageFilter.GaussianBlur(60))
        img.putalpha(Image.new("L", (W*SS, H*SS), 255)) if False else None
        # 简化: 用半透明黑框
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dsx = ImageDraw.Draw(shade)
        dsx.rectangle([0, 0, W, 120], fill=(0, 0, 30, 120))
        dsx.rectangle([0, H-180, W, H], fill=(0, 0, 30, 120))
        img_rgba = img.convert("RGBA")
        img_rgba.alpha_composite(shade)
        img = img_rgba.convert("RGB")
        d = ImageDraw.Draw(img)
        text(d, (W//2, 60), "— 慢动作 —", 36, fill=(200, 210, 255), sw=5)
    # 最后一个靶
    if t < hit_t:
        target(d, 640, 380, 52)
        text(d, (640, 300), "最后一个靶！", 34, fill=WHITE, sw=5)
    else:
        k = min(1.0, (t - hit_t) / 0.5)
        burst(d, 640, 380, k, col=YELLOW)
        if t < hit_t + 1.2:
            text(d, (640, 380), "命中！", 52, fill=YELLOW, sw=8)
    # 对射两人
    draw_player(d, 200, 640, 1.2, "red", facing=1, pose="draw" if t < 1.2 else "shoot", t=t)
    draw_player(d, 1080, 640, 1.2, "blue", facing=-1, pose="draw" if t < 1.2 else "shoot", t=t)
    # 交错箭
    if 1.4 <= t < 4.2:
        k = (t - 1.4) / 2.8
        ax1 = lerp(260, 640, ease(k)); ay1 = lerp(560, 400, k) - math.sin(k * math.pi) * 40
        ax2 = lerp(1020, 640, ease(k)); ay2 = lerp(560, 360, k) - math.sin(k * math.pi) * 30
        arrow(d, ax1 - 50, ay1 + 8, ax1, ay1, 1.3)
        arrow(d, ax2 + 50, ay2 + 8, ax2, ay2, 1.3)
    # 决胜箭
    if 4.6 <= t < hit_t:
        k = (t - 4.6) / (hit_t - 4.6)
        ax = lerp(260, 640, ease(k)); ay = lerp(560, 380, k) - math.sin(k * math.pi) * 90
        arrow(d, ax - 54, ay + 8, ax, ay, 1.5)
    # 胜利
    if t > hit_t + 0.7:
        pop = min(1.0, (t - hit_t - 0.7) / 0.4)
        sz = 110 * (0.5 + 0.5 * ease(pop))
        text(d, (W//2, 170), "胜利！", sz, fill=YELLOW, sw=12)
        confetti(d, t - hit_t, 46, seed=11)
        for i, xx in enumerate((150, 260, 370)):
            draw_player(d, xx, 640, 0.9, "red", facing=1, pose="cheer", t=t + i * 0.4)
    subtitle(d, "最后关头，一箭定胜负！团队合作才是王道！")
    return downscale(img)

def scene7(t, T):
    """安全提示"""
    img, d = base_canvas()
    ground(d, 560)
    # 大面罩特写
    pop = ease(min(1.0, t / 0.6))
    cx, cy = 400, 300
    sc = 2.6 * (0.7 + 0.3 * pop)
    d.rounded_rectangle([cx - 90*sc, cy - 70*sc, cx + 90*sc, cy + 40*sc], radius=40*sc, fill=DARK, outline=WHITE, width=6)
    d.line([cx - 66*sc, cy - 8*sc, cx + 66*sc, cy - 8*sc], fill=(110, 200, 255), width=int(10*sc))
    d.rectangle([cx - 56*sc, cy + 40*sc, cx + 56*sc, cy + 62*sc], fill=(90, 90, 110))
    text(d, (cx, cy + 150), "防护面罩", 40, fill=WHITE, sw=6)
    # 笑脸戴面罩角色
    draw_player(d, 880, 600, 1.6, "red", facing=-1, pose="cheer", t=t)
    # 勾选项
    checks = [("面罩 ✓", 150), ("护臂 ✓", 240), ("泡沫箭头 ✓", 330)]
    for i, (s, yy) in enumerate(checks):
        show = t > 0.9 + i * 0.5
        if show:
            k = ease(min(1.0, (t - (0.9 + i * 0.5)) / 0.25))
            text(d, (int(1080 - (1-k) * 60), yy), s, 42, fill=(140, 255, 170), sw=6)
    scene_title(d, "安全第一", 60, 90, color=(140, 255, 170))
    subtitle(d, "全程佩戴面罩，安全第一，享受快乐对战！")
    return downscale(img)

def scene8(t, T):
    """结束画面: 两队合影 + 邀请"""
    img, d = base_canvas()
    for cx in (200, 640, 1080):
        cloud(d, cx, 100, 1.2)
    ground(d, 560)
    confetti(d, t, 30, seed=21)
    # 两队排排站
    for i, xx in enumerate((330, 440, 550)):
        draw_player(d, xx, 640, 1.0, "red", facing=1, pose="cheer" if i == 1 else "stand", t=t + i * 0.5)
    for i, xx in enumerate((730, 840, 950)):
        draw_player(d, xx, 640, 1.0, "blue", facing=-1, pose="cheer" if i == 1 else "stand", t=t + i * 0.5)
    # 中间握手/击掌
    draw_player(d, 610, 620, 0.85, "red", facing=1, pose="cheer", t=t + 1)
    draw_player(d, 670, 620, 0.85, "blue", facing=-1, pose="cheer", t=t + 1.2)
    pop = ease(min(1.0, t / 0.7))
    text(d, (W//2, 150), "快来试试攻防箭！", 76 * (0.6 + 0.4 * pop), fill=YELLOW, sw=10)
    if t > 1.0:
        text(d, (W//2, 250), "组队来一场吧！", 46, fill=WHITE, sw=6)
    subtitle(d, "想玩吗？组队来一场吧！")
    return downscale(img)

SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8]
NARRATION = [
    "来一场刺激的攻防对战吧！攻防箭——融合射箭与闪避球的团队大战！",
    "场地分成两半，中间是安全区。每个人有弓和安全泡沫箭，被射中就出局，但接住箭可以复活队友！",
    "比赛开始！大家冲到中间抢箭，然后回到自己的攻击区开始对战！",
    "躲！射！接箭复活！利用掩体走位，团队配合最重要！",
    "别忘了攻击对方箭靶！先把所有靶子打掉也能获胜！",
    "最后关头，一箭定胜负！团队合作才是王道！",
    "全程佩戴面罩，安全第一，享受快乐对战！",
    "想玩吗？组队来一场吧！",
]

def render_frames():
    os.makedirs(OUT_FRAMES, exist_ok=True)
    idx = 0
    for si, (fn, dur) in enumerate(zip(SCENES, SCENE_DUR)):
        nframes = int(round(dur * FPS))
        for f in range(nframes):
            t = f / FPS
            frame = fn(t, dur)
            idx += 1
            frame.save(os.path.join(OUT_FRAMES, "f%05d.png" % idx))
        print("scene %d done (%d frames)" % (si + 1, nframes), flush=True)
    print("total frames:", idx)

# ---------- 程序化背景音乐 ----------
def render_music(path):
    sr = 44100
    n = int(sr * (TOTAL + 0.5))
    buf = np.zeros(n, dtype=np.float64)
    rng = np.random.default_rng(7)
    bpm = 126
    beat = 60.0 / bpm

    def add(sig, at):
        i0 = int(at * sr)
        i1 = min(n, i0 + len(sig))
        if i0 < n:
            buf[i0:i1] += sig[:i1 - i0]

    tt_beat = np.arange(int(0.14 * sr)) / sr
    kick = np.sin(2 * np.pi * (70 * tt_beat - 40 * tt_beat**2)) * np.exp(-tt_beat * 26)
    hat = (rng.standard_normal(len(tt_beat)) * np.exp(-tt_beat * 90)) * 0.12
    bass_notes = [110.0, 110.0, 130.8, 98.0]     # A2 A3? A2 C3 G2
    bt = 0.0
    bar = 0
    while bt < TOTAL:
        add(kick * 0.5, bt)
        add(kick * 0.4, bt + beat / 2)
        add(hat, bt + beat / 4)
        add(hat, bt + beat * 3 / 4)
        f0 = bass_notes[bar % 4]
        tb = np.arange(int(beat * 0.9 * sr)) / sr
        bsig = np.sign(np.sin(2 * np.pi * f0 * tb)) * np.exp(-tb * 5) * 0.10
        add(bsig, bt)
        if bar % 2 == 1:  # 琶音点缀
            for j, f1 in enumerate((440, 523.3, 659.3)):
                tl = np.arange(int(0.1 * sr)) / sr
                add(np.sin(2 * np.pi * f1 * tl) * np.exp(-tl * 22) * 0.07, bt + beat * j / 3)
        bt += beat
        bar += 1
    # 场景转场叮
    scene_starts = np.cumsum([0] + SCENE_DUR[:-1])
    for st_ in scene_starts:
        tl = np.arange(int(0.5 * sr)) / sr
        f = 880 * (1 + tl * 1.5)
        add(np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tl * 6) * 0.22, st_)
    # 射箭嗖声
    whoosh_times = [3.1, 21.5, 26.0, 37.0, 40.5, 44.0, 46.6, 49.4]
    for wt in whoosh_times:
        tl = np.arange(int(0.35 * sr)) / sr
        nz = rng.standard_normal(len(tl))
        env = np.sin(np.pi * tl / 0.35) ** 2
        add(nz * env * 0.10, wt)
    # 命中咚
    hit_times = [38.2, 41.2, 44.2, 52.2]
    for ht in hit_times:
        tl = np.arange(int(0.3 * sr)) / sr
        add(np.sin(2 * np.pi * (180 - 100 * tl) * tl) * np.exp(-tl * 14) * 0.3, ht)

    buf = np.clip(buf, -0.9, 0.9)
    pcm = (buf * 32767 * 0.85).astype(np.int16)
    import wave
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    print("music written:", path)

if __name__ == "__main__":
    import sys
    if "--music-only" in sys.argv:
        render_music(os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.wav"))
    else:
        render_frames()
        render_music(os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.wav"))
