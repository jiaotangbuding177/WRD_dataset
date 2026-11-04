#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""攻防箭小游戏宣传动画 - 8镜头代码动画渲染器
中间项目保留在本目录, 修改 SCENE_DUR / NARRATION / 各场景函数后重跑即可重渲染.
用法: python render.py            # 渲染全部帧+音乐
      python render.py --scene N  # 只渲染第N个镜头(1-8, 调试用)
      python render.py --music    # 只生成音乐
"""
import math, os, sys, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

W, H = 1280, 720
FPS = 24
SCENE_DUR = [5, 10, 5, 15, 10, 10, 5, 8]   # 分镜时长(秒), 共68s
TOTAL = sum(SCENE_DUR)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_FRAMES = os.path.join(HERE, "frames")

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_fonts = {}
def F(size):
    size = int(size)
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT_PATH, size)
    return _fonts[size]

RED    = (255, 77, 94);  RED_D  = (200, 40, 60)
BLUE   = (63, 169, 245); BLUE_D = (30, 110, 190)
SKIN   = (255, 214, 170)
DARK   = (45, 45, 65)
WHITE  = (255, 255, 255)
YELLOW = (255, 205, 60)
GREEN  = (110, 200, 110); GREEN_D = (80, 165, 85)
GRAY   = (160, 160, 170)

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)
def lerp(a, b, k):
    return a + (b - a) * k

def base_canvas():
    top, bot = (150, 210, 255), (215, 240, 255)
    img = Image.new("RGB", (W, H), top)
    d = ImageDraw.Draw(img)
    for i in range(H):
        k = i / H
        d.line([(0, i), (W, i)], fill=tuple(int(lerp(top[j], bot[j], k)) for j in range(3)))
    return img, d

def downscale(img):
    if img.size == (W, H):
        return img
    return img.resize((W, H), Image.LANCZOS)

def text(d, xy, s, size, fill=WHITE, anchor="mm", stroke=DARK, sw=None):
    sw = sw if sw is not None else max(2, int(size / 15))
    d.text(xy, s, font=F(size), fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=stroke)

def wrap(s, size, maxw):
    f = F(size)
    lines, cur = [], ""
    for ch in s:
        if f.getlength(cur + ch) > maxw and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines

def subtitle(d, s):
    size = 36
    lines = wrap(s, size, int(W * 0.84))
    lh = size + 14
    bh = lh * len(lines) + 26
    y0 = H - bh - 16
    d.rounded_rectangle([int(W * 0.05), y0, int(W * 0.95), y0 + bh], radius=18,
                        fill=(20, 20, 35), outline=WHITE, width=3)
    ty = y0 + 14 + lh // 2
    for ln in lines:
        text(d, (W // 2, ty), ln, size)
        ty += lh

def scene_title(d, s, size=64, y=110, color=YELLOW):
    text(d, (W // 2, y), s, size, fill=color, sw=int(size / 12))

# ---------- Q版角色与道具 ----------
def draw_player(d, x, y, s, team, facing=1, pose="stand", t=0.0, ghost=False):
    body = RED if team == "red" else BLUE
    body_d = RED_D if team == "red" else BLUE_D
    if ghost:
        body, body_d = GRAY, (120, 120, 130)
    bob = math.sin(t * 6) * 3 * s if pose == "stand" else 0
    jump = -abs(math.sin(t * 7)) * 16 * s if pose == "cheer" else 0
    x, y = x, y + bob + jump

    if pose == "down":
        d.ellipse([x - 26*s, y - 14*s, x + 26*s, y + 14*s], fill=body)
        d.ellipse([x + 10*s, y - 46*s, x + 48*s, y - 8*s], fill=SKIN)
        d.rounded_rectangle([x + 12*s, y - 38*s, x + 44*s, y - 26*s], radius=6*s, fill=DARK)
        for i in range(3):
            a = t * 4 + i * 2.09
            star(d, x + 29*s + math.cos(a) * 26*s, y - 62*s + math.sin(a) * 8*s, 7*s, YELLOW)
        return

    lean = 0.18 if pose == "run" else 0.0
    hx = x + lean * 20 * s * facing
    hip_y = y - 34 * s
    head_cy = y - 78 * s

    if pose == "run":
        ph = math.sin(t * 14)
        d.line([hx - 8*s, hip_y, hx + ph * 16 * s, y], fill=body_d, width=int(7*s))
        d.line([hx + 8*s, hip_y, hx - ph * 16 * s, y], fill=body_d, width=int(7*s))
    elif pose == "dodge":
        d.line([x - 12*s, hip_y, x - 16*s, y], fill=body_d, width=int(7*s))
        d.line([x + 12*s, hip_y, x + 18*s, y], fill=body_d, width=int(7*s))
    else:
        d.line([x - 8*s, hip_y, x - 10*s, y], fill=body_d, width=int(7*s))
        d.line([x + 8*s, hip_y, x + 10*s, y], fill=body_d, width=int(7*s))
    for fx in (x - 10*s, x + 10*s):
        d.ellipse([fx - 5*s, y - 4*s, fx + 5*s, y + 4*s], fill=DARK)

    d.rounded_rectangle([x - 17*s, y - 62*s, x + 17*s, y - 26*s], radius=12*s, fill=body)
    d.ellipse([x - 7*s, y - 52*s, x + 7*s, y - 38*s], fill=WHITE)

    bow_shown = pose in ("shoot", "draw")
    if pose == "cheer":
        sw_ = math.sin(t * 7) * 4
        d.line([x - 14*s, y - 56*s, x - 24*s, y - 80*s - sw_*s], fill=body_d, width=int(6*s))
        d.line([x + 14*s, y - 56*s, x + 24*s, y - 80*s + sw_*s], fill=body_d, width=int(6*s))
    elif bow_shown:
        ax_ = x + 26 * s * facing
        d.line([x, y - 50*s, ax_, y - 52*s], fill=body_d, width=int(6*s))
        pull = 14 * s if pose == "draw" else 4 * s
        d.line([x, y - 50*s, x - pull * facing, y - 48*s], fill=body_d, width=int(6*s))
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

    d.ellipse([hx - 22*s, head_cy - 22*s, hx + 22*s, head_cy + 22*s], fill=SKIN)
    d.pieslice([hx - 22*s, head_cy - 22*s, hx + 22*s, head_cy + 22*s], 180, 360, fill=body_d)
    d.rounded_rectangle([hx - 20*s, head_cy - 10*s, hx + 20*s, head_cy + 4*s], radius=8*s, fill=DARK)
    d.line([hx - 14*s, head_cy - 3*s, hx + 14*s, head_cy - 3*s], fill=(110, 200, 255), width=int(3*s))

def draw_bow(d, x, y, s, facing, pulled=False):
    col = (140, 90, 50)
    d.arc([x - 10*s, y - 26*s, x + 10*s, y + 26*s],
          start=90 if facing > 0 else -90, end=270 if facing > 0 else 90,
          fill=col, width=int(4*s))
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
               (x1 + math.cos(ang+2.5)*L*0.7, y1 + math.sin(ang+2.5)*L*0.7),
               (x1 + math.cos(ang-2.5)*L*0.7, y1 + math.sin(ang-2.5)*L*0.7)], fill=YELLOW)
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
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=max(2, int((1-k) * 10)))

def burst(d, cx, cy, k, col=YELLOW):
    r = 20 + k * 46
    for i in range(8):
        a = i * math.pi / 4 + k
        d.line([cx + r*0.45*math.cos(a), cy + r*0.45*math.sin(a),
                cx + r*math.cos(a), cy + r*math.sin(a)], fill=col, width=max(3, int(8*(1-k))))
    star(d, cx, cy, 18*(1-k) + 6, col)

def dust(d, x, y, t, col=(230, 230, 230)):
    for i in range(3):
        ph = (t * 2 + i * 0.5) % 1
        r = 6 + ph * 12
        d.ellipse([x - r, y - r - ph*14, x + r, y + r - ph*14], outline=col, width=2)

def confetti(d, t, n=40, seed=7):
    rnd = random.Random(seed)
    cols = [RED, BLUE, YELLOW, GREEN, (255, 150, 220)]
    for i in range(n):
        px = rnd.uniform(0, W)
        spd = rnd.uniform(90, 220)
        py = (rnd.uniform(0, H) + t * spd) % (H * 1.1) - H * 0.05
        a = t * 5 + i
        sz = rnd.uniform(4, 9)
        d.polygon([(px + math.cos(a)*sz, py), (px, py + math.sin(a)*sz),
                   (px - math.cos(a)*sz, py), (px, py - math.sin(a)*sz)], fill=cols[i % 5])

def ground(d, y=560):
    d.rectangle([0, y, W, y + 40], fill=GREEN)
    d.rectangle([0, y + 40, W, H], fill=GREEN_D)

def obstacle(d, cx, cy, w, h, col=(255, 170, 60)):
    d.rounded_rectangle([cx - w/2, cy - h/2, cx + w/2, cy + h/2], radius=int(h/4), fill=col)
    d.rounded_rectangle([cx - w/2 + 6, cy - h/2 + 8, cx + w/2 - 6, cy - h/2 + h*0.35], radius=10, fill=(255, 210, 130))

def target(d, cx, cy, r, rings=(WHITE, RED, WHITE, RED)):
    for i, c in enumerate(rings):
        rr = r * (1 - i * 0.22)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=c, outline=DARK, width=2)
    d.ellipse([cx - r*0.16, cy - r*0.16, cx + r*0.16, cy + r*0.16], fill=YELLOW)

def cloud(d, cx, cy, s=1.0):
    for ox, oy, r in ((-30, 8, 20), (0, 0, 28), (32, 8, 20)):
        d.ellipse([cx+ox*s - r*s, cy+oy*s - r*s, cx+ox*s + r*s, cy+oy*s + r*s], fill=WHITE)

# ============================================================
# 8 个镜头
# ============================================================
def scene1(t, T):
    """镜头1 开场标题: 场景拉近→拉弦→箭飞出, 标题弹出 (2x世界画布推近)"""
    WS, HS = W * 2, H * 2
    img = Image.new("RGB", (WS, HS), (150, 210, 255))
    d = ImageDraw.Draw(img)
    for i in range(HS):
        k = i / HS
        d.line([(0, i), (WS, i)], fill=(int(lerp(150, 215, k)), int(lerp(210, 240, k)), 255))
    for cx in (180, 640, 1080):
        cloud(d, cx * 2, 220 + (cx % 3) * 60, 2.2)
    d.rectangle([0, 1120, WS, 1200], fill=GREEN)
    d.rectangle([0, 1200, WS, HS], fill=GREEN_D)
    d.line([W, 1120, W, HS], fill=WHITE, width=12)
    k = ease(t / T)
    for i, xx in enumerate((300, 420, 540)):
        draw_player(d, xx*2, 1280, 2.4, "red", facing=1, pose="stand", t=t + i)
    for i, xx in enumerate((740, 860, 980)):
        draw_player(d, xx*2, 1280, 2.4, "blue", facing=-1, pose="stand", t=t + i)
    # 前景拉弦弓箭手
    if t < T * 0.62:
        draw_player(d, 1280, 1400, 4.4, "red", facing=1, pose="draw", t=t)
    else:
        draw_player(d, 1280, 1400, 4.4, "red", facing=1, pose="shoot", t=t)
        ak = ease((t - T * 0.62) / (T * 0.38))
        ax = 1400 + ak * 1800
        for tr in range(5):
            arrow(d, ax - 120 - tr*92, 1280 - tr*8, ax - 40 - tr*92, 1280 - tr*8, 2.4, col=(200, 200, 210))
        arrow(d, ax - 120, 1280, ax, 1280, 2.8)
        if ak < 0.35:
            flash_ring(d, 1400, 1280, ak / 0.35, rmax=180)
    # 推近裁切
    cw = lerp(WS, WS * 0.42, k)
    ch = lerp(HS, HS * 0.42, k)
    fcx = lerp(WS / 2, 1280, k)
    fcy = lerp(HS * 0.55, 1200, k)
    x0 = max(0, min(WS - cw, fcx - cw / 2))
    y0 = max(0, min(HS - ch, fcy - ch / 2))
    frame = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
    df = ImageDraw.Draw(frame)
    ts_ = t / T
    if ts_ > 0.12:
        pop = ease(min(1.0, (ts_ - 0.12) / 0.18))
        text(df, (W // 2, 150), "攻防箭小游戏", 92 * (0.6 + 0.4 * pop), fill=YELLOW, sw=10)
        if pop >= 1 and ts_ < 0.8:
            text(df, (W // 2, 245), "射箭 × 闪避球 · 团队大战", 32, fill=WHITE, sw=4)
    subtitle(df, NARRATION[0])
    return frame

def scene2(t, T):
    """镜头2 规则介绍: 俯视场地 → 装备展示"""
    if t < T * 0.52:
        img = Image.new("RGB", (W, H), (250, 247, 238))
        d = ImageDraw.Draw(img)
        fx0, fy0, fx1, fy1 = 120, 140, 1160, 560
        d.rounded_rectangle([fx0, fy0, fx1, fy1], radius=30, outline=DARK, width=5)
        fw = fx1 - fx0
        d.rectangle([fx0, fy0, fx0 + fw*0.36, fy1], fill=(255, 120, 130))
        d.rectangle([fx0 + fw*0.36, fy0, fx0 + fw*0.64, fy1], fill=(255, 235, 150))
        d.rectangle([fx0 + fw*0.64, fy0, fx1, fy1], fill=(110, 190, 255))
        d.rounded_rectangle([fx0, fy0, fx1, fy1], radius=30, outline=DARK, width=5)
        d.line([(fx0+fx1)/2, fy0, (fx0+fx1)/2, fy1], fill=WHITE, width=6)
        text(d, (fx0 + fw*0.18, fy0 + 70), "红队区", 46, fill=WHITE, stroke=RED_D)
        text(d, (fx0 + fw*0.5, fy0 + 70), "安全中立区", 34, fill=DARK, stroke=WHITE)
        text(d, (fx0 + fw*0.82, fy0 + 70), "蓝队区", 46, fill=WHITE, stroke=BLUE_D)
        for ox, oy in ((0.12, 0.5), (0.22, 0.82), (0.78, 0.5), (0.88, 0.82)):
            cx, cy = fx0 + fw*ox, fy0 + (fy1-fy0)*oy
            d.rounded_rectangle([cx-65, cy-23, cx+65, cy+23], radius=20, fill=(255, 170, 60), outline=DARK, width=3)
            text(d, (cx, cy), "障碍", 24, fill=DARK, stroke=WHITE, sw=3)
        for i in range(3):
            ty = fy0 + (fy1-fy0)*(0.28 + i*0.24)
            target(d, fx0 + fw*0.07, ty, 26)
            target(d, fx1 - fw*0.07, ty, 26)
        text(d, (fx0 + fw*0.07, fy1 - 26), "箭靶", 24, fill=WHITE, stroke=RED_D, sw=3)
        text(d, (fx1 - fw*0.07, fy1 - 26), "箭靶", 24, fill=WHITE, stroke=BLUE_D, sw=3)
        for i in range(5):
            px = fx0 + 220 + i * 55
            cy1 = fy0 + (fy1-fy0)*0.62
            cy2 = fy0 + (fy1-fy0)*0.42
            d.ellipse([px-16, cy1-16, px+16, cy1+16], fill=RED, outline=WHITE, width=3)
            d.ellipse([px-16, cy2-16, px+16, cy2+16], fill=BLUE, outline=WHITE, width=3)
        scene_title(d, "场地与装备", 54, 80)
        subtitle(d, NARRATION[1])
        return img
    img, d = base_canvas()
    ground(d, 540)
    tt = (t - T * 0.52) / (T * 0.48)
    cards = ["反曲弓+泡沫箭", "防护面罩", "护臂"]
    cw_, ch_ = 300, 320
    for i, label in enumerate(cards):
        cx = 240 + i * 400
        pop = ease(min(1.0, max(0.0, (tt - i * 0.18) / 0.3)))
        yy = 190 + (1 - pop) * 60
        d.rounded_rectangle([cx - cw_//2, yy, cx + cw_//2, yy + ch_], radius=26, fill=WHITE, outline=DARK, width=5)
        bx, by = cx, yy + 115
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
        text(d, (cx, yy + ch_ - 55), label, 34, fill=DARK, stroke=WHITE, sw=4)
    scene_title(d, "安全装备", 54, 80)
    subtitle(d, NARRATION[1])
    return img

def scene3(t, T):
    """镜头3 开局冲刺: 两队冲向中立区抢箭再回撤"""
    img, d = base_canvas()
    cloud(d, 250, 100, 1.1)
    cloud(d, 950, 120, 1.0)
    ground(d, 560)
    d.line([W // 2, 560, W // 2, H], fill=WHITE, width=6)
    d.ellipse([W//2 - 70, 630, W//2 + 70, 690], fill=(240, 240, 245), outline=DARK, width=4)
    for i in range(4):
        a = i * math.pi / 2 + 0.4
        arrow(d, W//2 + 30*math.cos(a), 655 + 16*math.sin(a), W//2 + 55*math.cos(a), 655 + 22*math.sin(a), 0.9)
    k = math.sin(min(1.0, t / T) * math.pi)
    shake = math.sin(t * 40) * 3 * (0.4 + k)
    for i, off in enumerate((-90, -30, 30)):
        xr = W//2 - 460 + k * 380 + off * (1 - k * 0.7)
        xb = W//2 + 460 - k * 380 - off * (1 - k * 0.7)
        draw_player(d, xr + shake, 640 - i * 6, 1.05, "red", facing=1, pose="run", t=t + i * 0.3)
        draw_player(d, xb + shake, 640 - i * 6, 1.05, "blue", facing=-1, pose="run", t=t + i * 0.3)
        dust(d, xr - 30, 655, t * 3 + i)
        dust(d, xb + 30, 655, t * 3 + i + 0.4)
    for i in range(8):
        yy = 470 + i * 26
        ln = 60 + (i % 3) * 40
        xx = (t * 900 + i * 210) % (W + 200) - 100
        d.line([xx, yy, xx + ln, yy], fill=WHITE, width=4)
    scene_title(d, "比赛开始！", 56, 90)
    subtitle(d, NARRATION[2])
    return img

def scene4(t, T):
    """镜头4 激烈攻防: 射箭/闪避/接箭复活/出局"""
    img, d = base_canvas()
    ground(d, 560)
    obstacle(d, 380, 530, 170, 130)
    obstacle(d, 940, 530, 150, 110)
    shot_r_t, catch_t, revive_t, shot_b_t, out_t = 0.75, 4.8, 7.2, 9.3, 11.7

    red_pose = "draw" if t < 1.0 else "shoot"
    blue_pose, blue_y = "stand", 640
    if t >= out_t:
        red_pose = "down"
    arrowA = None
    if shot_r_t <= t < catch_t:
        k = ease((t - shot_r_t) / (catch_t - shot_r_t))
        arrowA = (lerp(360, 1010, k), lerp(560, 590, k))
        if k > 0.5:
            blue_pose, blue_y = "dodge", 655
    if catch_t <= t < catch_t + 0.5:
        blue_pose = "catch"
        flash_ring(d, 1030, 570, (t - catch_t) / 0.5, col=(120, 255, 160))
    elif catch_t + 0.5 <= t < shot_b_t:
        blue_pose = "draw"

    # 复活的队友(先灰后亮)
    revived = t >= revive_t
    if revived:
        k = ease(min(1.0, (t - revive_t) / 0.6))
        draw_player(d, 1130, 655, 1.0, "blue", facing=-1, pose="stand", t=t, ghost=(k < 1))
        if k < 1:
            flash_ring(d, 1130, 605, k, col=(255, 230, 120), rmax=120)
        star(d, 1130, 555 + (0 if k < 1 else -10), 14 + (10 * math.sin(t*10) if k < 1 else 4*math.sin(t*8)), YELLOW)
        if t < revive_t + 1.2:
            pop = min(1.0, (t - revive_t) / 0.25)
            text(d, (1130, 505), "复活！", 46 * (0.5 + 0.5 * pop), fill=(120, 255, 160), sw=7)
    else:
        draw_player(d, 1130, 655, 1.0, "blue", facing=-1, pose="stand", t=t, ghost=True)
        text(d, (1130, 530), "出局中", 26, fill=GRAY, sw=4)

    arrowB = None
    if shot_b_t <= t < out_t:
        k = ease((t - shot_b_t) / (out_t - shot_b_t))
        arrowB = (lerp(1010, 360, k), lerp(580, 560, k))
    if t >= out_t and t < out_t + 0.9:
        k = (t - out_t) / 0.5
        if k < 1:
            burst(d, 330, 560, k, col=RED)
            text(d, (330, 470), "出局！", 52 * (0.5 + 0.5 * min(1, k*2)), fill=RED, sw=8)

    draw_player(d, 300, 640, 1.1, "red", facing=1, pose=red_pose, t=t)
    draw_player(d, 1040, blue_y, 1.1, "blue", facing=-1, pose=blue_pose, t=t)
    if arrowA:
        arrow(d, arrowA[0] - 46, arrowA[1], arrowA[0], arrowA[1], 1.2)
    if arrowB:
        arrow(d, arrowB[0] + 46, arrowB[1], arrowB[0], arrowB[1], 1.2)

    if t < 1.2:
        scene_title(d, "激烈攻防！", 54, 110)
    elif revive_t <= t < revive_t + 1.4:
        text(d, (W//2, 110), "接住飞箭 = 复活队友！", 44, fill=(120, 255, 160), sw=7)
    elif t >= out_t + 0.6:
        text(d, (W//2, 110), "被击中就出局！", 44, fill=RED, sw=7)
    subtitle(d, NARRATION[3])
    return img

def scene5(t, T):
    """镜头5 攻击箭靶: 三箭依次命中"""
    img, d = base_canvas()
    ground(d, 560)
    hits = [2.2, 5.0, 7.8]
    txs = [980, 1080, 980]
    tys = [430, 500, 570]
    starts = [0.6, 2.2, 5.0]
    fallen = 0
    for i, ht in enumerate(hits):
        if t < ht:
            target(d, txs[i], tys[i], 40)
        else:
            fallen += 1
            k = min(1.0, (t - ht) / 0.5)
            r = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
            dr = ImageDraw.Draw(r)
            for j, c in enumerate((WHITE, RED, WHITE, RED)):
                rr = 40 * (1 - j * 0.22)
                dr.ellipse([110 - rr, 110 - rr, 110 + rr, 110 + rr], fill=c, outline=DARK, width=2)
            dr.ellipse([110 - 7, 110 - 7, 110 + 7, 110 + 7], fill=YELLOW)
            r = r.rotate(k * 80, center=(110, 160), expand=False)
            img.paste(r, (txs[i] - 110, tys[i] - 40), r)
            d = ImageDraw.Draw(img)
            if k < 1:
                burst(d, txs[i], tys[i], k, col=YELLOW)
                text(d, (txs[i], tys[i] - 80), "命中！", 44, fill=YELLOW, sw=7)
        if starts[i] <= t < ht:
            k = ease((t - starts[i]) / (ht - starts[i]))
            ax = lerp(240, txs[i], k); ay = lerp(560, tys[i], k) - math.sin(k * math.pi) * 60
            arrow(d, ax - 46, ay + 6, ax, ay, 1.2)
    shooting = any(s <= t < ht for s, ht in zip(starts, hits))
    draw_player(d, 220, 640, 1.15, "red", facing=1, pose="draw" if shooting else "shoot", t=t)
    text(d, (W // 2, 100), "击落箭靶 %d/3" % fallen, 52, fill=YELLOW, sw=8)
    subtitle(d, NARRATION[4])
    return img

def scene6(t, T):
    """镜头6 高潮决胜: 慢动作交错箭 + 最后一靶被击落 + 胜利"""
    img, d = base_canvas()
    ground(d, 560)
    slow_t, hit_t = 1.0, 6.2
    if slow_t <= t < hit_t:
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dsx = ImageDraw.Draw(shade)
        dsx.rectangle([0, 0, W, 110], fill=(0, 0, 30, 110))
        dsx.rectangle([0, H - 190, W, H], fill=(0, 0, 30, 110))
        ir = img.convert("RGBA"); ir.alpha_composite(shade)
        img = ir.convert("RGB")
        d = ImageDraw.Draw(img)
        text(d, (W//2, 55), "— 慢 动 作 —", 34, fill=(200, 210, 255), sw=5)
    if t < hit_t:
        target(d, 640, 380, 52)
        text(d, (640, 295), "最后一个靶！", 34, fill=WHITE, sw=5)
    else:
        k = min(1.0, (t - hit_t) / 0.5)
        burst(d, 640, 380, k, col=YELLOW)
        if t < hit_t + 1.2:
            text(d, (640, 380), "命中！", 52, fill=YELLOW, sw=8)
    draw_player(d, 200, 640, 1.2, "red", facing=1, pose="draw" if t < 1.2 else "shoot", t=t)
    draw_player(d, 1080, 640, 1.2, "blue", facing=-1, pose="draw" if t < 1.2 else "shoot", t=t)
    if 1.4 <= t < 4.2:
        k = (t - 1.4) / 2.8
        ax1 = lerp(260, 640, ease(k)); ay1 = lerp(560, 400, k) - math.sin(k * math.pi) * 40
        ax2 = lerp(1020, 640, ease(k)); ay2 = lerp(560, 360, k) - math.sin(k * math.pi) * 30
        arrow(d, ax1 - 50, ay1 + 8, ax1, ay1, 1.3)
        arrow(d, ax2 + 50, ay2 + 8, ax2, ay2, 1.3)
    if 4.6 <= t < hit_t:
        k = (t - 4.6) / (hit_t - 4.6)
        ax = lerp(260, 640, ease(k)); ay = lerp(560, 380, k) - math.sin(k * math.pi) * 90
        arrow(d, ax - 54, ay + 8, ax, ay, 1.5)
    if t > hit_t + 0.7:
        pop = ease(min(1.0, (t - hit_t - 0.7) / 0.4))
        text(d, (W//2, 170), "胜利！", 110 * (0.5 + 0.5 * pop), fill=YELLOW, sw=12)
        confetti(d, t - hit_t, 46, seed=11)
        for i, xx in enumerate((150, 260, 370)):
            draw_player(d, xx, 660, 0.9, "red", facing=1, pose="cheer", t=t + i * 0.4)
    subtitle(d, NARRATION[5])
    return img

def scene7(t, T):
    """镜头7 安全提示"""
    img, d = base_canvas()
    ground(d, 560)
    pop = ease(min(1.0, t / 0.6))
    cx, cy = 380, 300
    sc = 2.6 * (0.7 + 0.3 * pop)
    d.rounded_rectangle([cx - 90*sc, cy - 70*sc, cx + 90*sc, cy + 40*sc], radius=40*sc, fill=DARK, outline=WHITE, width=6)
    d.line([cx - 66*sc, cy - 8*sc, cx + 66*sc, cy - 8*sc], fill=(110, 200, 255), width=int(10*sc))
    d.rectangle([cx - 56*sc, cy + 40*sc, cx + 56*sc, cy + 62*sc], fill=(90, 90, 110))
    text(d, (cx, cy + 150), "防护面罩", 40, fill=WHITE, sw=6)
    draw_player(d, 880, 600, 1.6, "red", facing=-1, pose="cheer", t=t)
    for i, (s, yy) in enumerate((("面罩 ✓", 160), ("护臂 ✓", 250), ("泡沫箭头 ✓", 340))):
        if t > 0.9 + i * 0.5:
            k = ease(min(1.0, (t - (0.9 + i * 0.5)) / 0.25))
            text(d, (int(1090 - (1-k) * 60), yy), s, 42, fill=(140, 255, 170), sw=6)
    scene_title(d, "安全第一", 60, 80, color=(140, 255, 170))
    subtitle(d, NARRATION[6])
    return img

def scene8(t, T):
    """镜头8 结束画面: 两队合影 + 邀请"""
    img, d = base_canvas()
    cloud(d, 200, 100, 1.2)
    cloud(d, 640, 90, 1.0)
    cloud(d, 1080, 105, 1.2)
    ground(d, 560)
    confetti(d, t, 30, seed=21)
    for i, xx in enumerate((330, 440, 550)):
        draw_player(d, xx, 640, 1.0, "red", facing=1, pose="cheer" if i == 1 else "stand", t=t + i * 0.5)
    for i, xx in enumerate((730, 840, 950)):
        draw_player(d, xx, 640, 1.0, "blue", facing=-1, pose="cheer" if i == 1 else "stand", t=t + i * 0.5)
    draw_player(d, 610, 620, 0.85, "red", facing=1, pose="cheer", t=t + 1)
    draw_player(d, 670, 620, 0.85, "blue", facing=-1, pose="cheer", t=t + 1.2)
    pop = ease(min(1.0, t / 0.7))
    text(d, (W//2, 150), "快来试试攻防箭！", 76 * (0.6 + 0.4 * pop), fill=YELLOW, sw=10)
    if t > 1.0:
        text(d, (W//2, 250), "组队来一场吧！", 46, fill=WHITE, sw=6)
    subtitle(d, NARRATION[7])
    return img

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

def render_frames(only=None):
    os.makedirs(OUT_FRAMES, exist_ok=True)
    idx = 0
    for si, (fn, dur) in enumerate(zip(SCENES, SCENE_DUR)):
        if only and si + 1 != only:
            idx += int(round(dur * FPS))
            continue
        nframes = int(round(dur * FPS))
        for f in range(nframes):
            t = f / FPS
            frame = fn(t, dur)
            fn_idx = idx + f + 1
            frame.save(os.path.join(OUT_FRAMES, "f%05d.png" % fn_idx))
        idx += nframes
        print("scene %d done (%d frames)" % (si + 1, nframes), flush=True)
    print("total frames:", idx)

# ---------- 程序化背景音乐(126bpm 电子节拍 + 转场音效) ----------
def render_music(path):
    sr = 44100
    n = int(sr * (TOTAL + 0.5))
    buf = np.zeros(n)
    rng = np.random.default_rng(7)
    def add(sig, at):
        i0 = int(at * sr)
        i1 = min(n, i0 + len(sig))
        if i0 < n:
            buf[i0:i1] += sig[:i1 - i0]
    bpm = 126
    beat = 60.0 / bpm
    tt = np.arange(int(0.14 * sr)) / sr
    kick = np.sin(2 * np.pi * (70 * tt - 40 * tt**2)) * np.exp(-tt * 26)
    hat = (rng.standard_normal(len(tt)) * np.exp(-tt * 90)) * 0.12
    bass_notes = [110.0, 110.0, 130.8, 98.0]
    bt, bar = 0.0, 0
    while bt < TOTAL:
        add(kick * 0.5, bt)
        add(kick * 0.4, bt + beat / 2)
        add(hat, bt + beat / 4)
        add(hat, bt + beat * 3 / 4)
        tb = np.arange(int(beat * 0.9 * sr)) / sr
        add(np.sign(np.sin(2 * np.pi * bass_notes[bar % 4] * tb)) * np.exp(-tb * 5) * 0.10, bt)
        if bar % 2 == 1:
            for j, f1 in enumerate((440, 523.3, 659.3)):
                tl = np.arange(int(0.1 * sr)) / sr
                add(np.sin(2 * np.pi * f1 * tl) * np.exp(-tl * 22) * 0.07, bt + beat * j / 3)
        bt += beat
        bar += 1
    scene_starts = np.cumsum([0] + SCENE_DUR[:-1])
    for st_ in scene_starts:
        tl = np.arange(int(0.5 * sr)) / sr
        f = 880 * (1 + tl * 1.5)
        add(np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tl * 6) * 0.22, float(st_))
    for wt in (3.1, 20.8, 29.3, 36.4, 39.2, 42.0, 48.6, 51.2):   # 射箭嗖声
        tl = np.arange(int(0.35 * sr)) / sr
        add(rng.standard_normal(len(tl)) * np.sin(np.pi * tl / 0.35) ** 2 * 0.10, wt)
    for ht in (37.4, 40.2, 43.0, 51.3):                          # 命中咚
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
    only = None
    if "--scene" in sys.argv:
        only = int(sys.argv[sys.argv.index("--scene") + 1])
    if "--music" in sys.argv or only is None and "--frames-only" not in sys.argv and "--scene" not in sys.argv:
        render_music(os.path.join(HERE, "music.wav"))
    if "--music" not in sys.argv:
        render_frames(only)
