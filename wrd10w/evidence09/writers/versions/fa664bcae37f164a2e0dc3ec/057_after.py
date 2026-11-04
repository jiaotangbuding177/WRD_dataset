#!/usr/bin/env python3
# -*- coding: utf-8 -*- """攻防箭宣传动画渲染器：纯代码卡通Q版逐帧动画 + 字幕 + 合成配乐/SFX。"""
import os, math, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = "/workspace/gongfangjian_project"
FRAMES = os.path.join(ROOT, "frames")
AUDIODIR = os.path.join(ROOT, "audio")
OUTDIR = "/workspace/outputs"
FPS = 30
W, H = 1280, 720            # 输出尺寸
CW, CH = 1920, 1080         # 虚拟画布（世界坐标）
DUR = [5, 10, 5, 15, 10, 10, 5, 6]   # 每镜头时长
TOTAL = sum(DUR)

# ---------- 字体 ----------
def _find_font(weight="Regular"):
    for p in [f"/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc",
              f"/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}-Regular.ttc"]:
        if os.path.exists(p): return p
    import glob
    g = glob.glob("/usr/share/fonts/**/*CJK*", recursive=True)
    return g[0] if g else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_R = _find_font("Regular")
FONT_B = _find_font("Bold") if os.path.exists(_find_font("Bold")) else FONT_R
_font_cache = {}
def font(sz, bold=True):
    key = (sz, bold)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONT_B if bold else FONT_R, sz)
    return _font_cache[key]

# ---------- 颜色 ----------
RED    = (235, 60, 55);  RED_D  = (168, 32, 30)
BLUE   = (45, 115, 235); BLUE_D = (28, 70, 165)
SKIN   = (255, 221, 186)
FLOOR  = (238, 200, 138)
FLOOR2 = (222, 180, 116)
SAFEY  = (255, 208, 66)
WHITE  = (255, 255, 255)
INK    = (45, 40, 45)

def mix(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))

def ease(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)

def ease_out(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3

def clamp(v, a, b): return max(a, min(b, v))

# ---------- 文字精灵 ----------
def text_sprite(text, size, fill=WHITE, stroke=(30, 25, 35), sw=None, bold=True):
    f = font(size, bold)
    if sw is None: sw = max(2, size // 12)
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    box = d.textbbox((0, 0), text, font=f, stroke_width=sw)
    w, h = box[2] - box[0], box[3] - box[1]
    img = Image.new("RGBA", (w + sw * 2 + 8, h + sw * 2 + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((sw + 4 - box[0], sw + 4 - box[1]), text, font=f, fill=fill,
           stroke_width=sw, stroke_fill=stroke)
    return img

def paste_center(base, spr, cx, cy, scale=1.0, alpha=1.0, rot=0):
    if alpha <= 0.01: return
    if scale != 1.0 or rot:
        w, h = spr.size
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        spr = spr.resize((nw, nh), Image.LANCZOS)
    if rot:
        spr = spr.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        a = spr.getchannel("A").point(lambda v: int(v * alpha))
        spr = spr.copy(); spr.putalpha(a)
    base.alpha_composite(spr, (int(cx - spr.width / 2), int(cy - spr.height / 2)))

def pop_scale(t, t0, dur=0.45):
    """弹性弹出缩放"""
    if t < t0: return 0.0
    p = (t - t0) / dur
    if p >= 1: return 1.0
    return 1 + 0.28 * math.sin(min(p, 1) * math.pi) * (1 - p) + 0.9 * ease_out(p)

# ---------- Q版小人 ----------
def player_sprite(team, pose="stand", t=0.0, facing=1, bow=True, scale=1.0):
    """返回 RGBA 小人精灵，脚底位于精灵底部中央。"""
    main, dark = (RED, RED_D) if team == "red" else (BLUE, BLUE_D)
    S = 340
    img = Image.new("RGBA", (S, int(S * 1.32)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = S // 2
    foot_y = img.height - 14
    run = pose == "run"
    shoot = pose == "shoot"
    dodge = pose == "dodge"
    cheer = pose == "cheer"
    lean = 0
    if run: lean = 14 * facing
    if dodge: lean = -10 * facing
    # 腿
    hip_y = foot_y - 108
    if run:
        ph = math.sin(t * 14)
        for i, sgn in enumerate((1, -1)):
            dx = sgn * 22 + ph * sgn * 26
            knee = foot_y - 44 + abs(ph * sgn) * 16
            d.line([(cx + sgn * 12, hip_y), (cx + dx, knee), (cx + dx * 1.25, foot_y)],
                   fill=INK, width=26, joint="curve")
            d.ellipse([cx + dx * 1.25 - 24, foot_y - 16, cx + dx * 1.25 + 24, foot_y + 12], fill=INK)
    else:
        for sgn in (1, -1):
            d.line([(cx + sgn * 16, hip_y), (cx + sgn * 20, foot_y)], fill=INK, width=26)
            d.ellipse([cx + sgn * 20 - 24, foot_y - 14, cx + sgn * 20 + 24, foot_y + 12], fill=INK)
    # 身体（豆形）
    bob = math.sin(t * 6) * 3 if not run else 0
    body_top = foot_y - 200 + bob
    d.ellipse([cx - 62 + lean * 0.3, body_top, cx + 62 + lean * 0.3, body_top + 118], fill=main)
    d.ellipse([cx - 62 + lean * 0.3, body_top + 74, cx + 62 + lean * 0.3, body_top + 122], fill=dark)
    d.ellipse([cx - 40 + lean * 0.3, body_top + 16, cx + 30 + lean * 0.3, body_top + 70], fill=mix(main, WHITE, 0.28))
    # 后臂
    arm_back_y = body_top + 34
    if cheer:
        d.line([(cx - 40 * facing, arm_back_y), (cx - 78 * facing, arm_back_y - 66)], fill=main, width=24)
        d.ellipse([cx - 92 * facing - 14, arm_back_y - 84, cx - 92 * facing + 14, arm_back_y - 56], fill=SKIN)
    elif shoot:
        d.line([(cx - 34 * facing, arm_back_y), (cx - 60 * facing, arm_back_y + 30)], fill=main, width=24)
        d.ellipse([cx - 60 * facing - 13, arm_back_y + 18, cx - 60 * facing + 13, arm_back_y + 44], fill=SKIN)
    else:
        d.line([(cx - 34 * facing, arm_back_y), (cx - 52 * facing, arm_back_y + 44)], fill=main, width=24)
        d.ellipse([cx - 52 * facing - 13, arm_back_y + 32, cx - 52 * facing + 13, arm_back_y + 58], fill=SKIN)
    # 头
    head_cy = body_top - 92 + bob
    hr = 96
    d.ellipse([cx - hr, head_cy - hr, cx + hr, head_cy + hr], fill=SKIN)
    d.ellipse([cx - hr, head_cy - hr, cx + hr, head_cy + hr], outline=INK, width=5)
    # 头带
    d.rounded_rectangle([cx - hr, head_cy - hr - 6, cx + hr, head_cy - hr + 44], 26, fill=main)
    d.ellipse([cx + (hr - 26) * facing - 20, head_cy - hr - 16, cx + (hr - 26) * facing + 20, head_cy - hr + 24], fill=main)
    # 面罩
    d.rounded_rectangle([cx - hr + 6, head_cy - 52, cx + hr - 6, head_cy + 26], 34, fill=(70, 68, 80))
    d.rounded_rectangle([cx - hr + 14, head_cy - 44, cx + hr - 14, head_cy + 2], 26,
                        outline=(150, 148, 165), width=4)
    for gx in range(-2, 3):
        d.line([(cx + gx * 30, head_cy - 40), (cx + gx * 30, head_cy + 0)], fill=(120, 118, 135), width=6)
    d.ellipse([cx - 40, head_cy - 48, cx + 8, head_cy - 30], fill=(200, 200, 214))
    # 腮红
    for sgn in (1, -1):
        d.ellipse([cx + sgn * 62 - 16, head_cy + 40, cx + sgn * 62 + 16, head_cy + 58], fill=(255, 150, 140))
    # 微笑
    d.arc([cx - 30, head_cy + 34, cx + 30, head_cy + 72], 20, 160, fill=INK, width=7)
    # 弓与持弓臂
    if bow:
        arm_y = head_cy + 66
        if shoot:
            pull = clamp((t - 0.0) / 1.0, 0, 1)
            bx = cx + 118 * facing
            d.line([(cx + 20 * facing, arm_y), (bx - 10 * facing, arm_y)], fill=main, width=24)
            d.ellipse([bx - 24 * facing - 13, arm_y - 13, bx - 24 * facing + 13, arm_y + 13], fill=SKIN)
            draw_bow(d, bx, arm_y, facing, pull, True, team)
        elif cheer:
            pass
        else:
            bx = cx + 96 * facing
            by = body_top + 30
            d.line([(cx + 26 * facing, arm_y - 30), (bx, by + 10)], fill=main, width=24)
            d.ellipse([bx - 14, by - 3, bx + 14, by + 23], fill=SKIN)
            draw_bow(d, bx, by, facing, 0, False, team, angle=-30)
    return img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

def draw_bow(d, cx, cy, facing, pull, arrow, team, angle=0):
    """在 draw 上画反曲弓；facing=1 朝右。"""
    bowcol = (150, 100, 50)
    R = 88
    # 旋转：用简单平移近似（angle 小）
    a = math.radians(angle) * facing
    def pt(dx, dy):
        return (cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a))
    top = pt(0, -R); bot = pt(0, R)
    d.line([top, (cx, cy)], fill=bowcol, width=12)
    d.line([(cx, cy), bot], fill=bowcol, width=12)
    d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(90, 60, 30))
    nock = pt(-pull * 46, 0)
    d.line([top, nock, bot], fill=(240, 240, 240), width=4)
    if arrow and pull > 0.02:
        tip = pt(60 + (1 - pull) * 30, 0)
        tail = pt(-pull * 40, 0)
        d.line([tail, tip], fill=(90, 62, 40), width=8)
        foam = (RED if team == "red" else BLUE)
        d.ellipse([tip[0] - 14, tip[1] - 14, tip[0] + 14, tip[1] + 14], fill=foam, outline=INK, width=3)
        for fy in (-8, 8):
            t1 = pt(-pull * 40 - 16, fy); t2 = pt(-pull * 40 + 4, fy * 2.6)
            d.line([t1, t2], fill=(250, 250, 250), width=5)

def paste_player(base, team, x, y, pose="stand", t=0.0, facing=1, bow=True, scale=1.0, rot=0, alpha=1.0):
    spr = player_sprite(team, pose, t, facing, bow, scale)
    if rot: spr = spr.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        a = spr.getchannel("A").point(lambda v: int(v * alpha)); spr = spr.copy(); spr.putalpha(a)
    base.alpha_composite(spr, (int(x - spr.width / 2), int(y - spr.height)))
    return spr.height

# ---------- 场景元素 ----------
def draw_arrow_fx(base, x, y, ang, team, trail=6, scale=1.0):
    """飞行的泡沫箭（带拖尾），ang 弧度，速度方向。"""
    col = RED if team == "red" else BLUE
    for i in range(trail, 0, -1):
        gx = x - math.cos(ang) * i * 26 * scale
        gy = y - math.sin(ang) * i * 26 * scale
        a = int(90 * (1 - i / (trail + 1)))
        ghost = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        gd = ImageDraw.Draw(ghost)
        gd.ellipse([18, 18, 42, 42], fill=col + (a,))
        base.alpha_composite(ghost, (int(gx - 30), int(gy - 30)))
    L = 46 * scale
    x2, y2 = x - math.cos(ang) * L, y - math.sin(ang) * L
    d = ImageDraw.Draw(base)
    d.line([(x, y), (x2, y2)], fill=(96, 66, 42), width=int(9 * scale))
    r = 15 * scale
    d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=INK, width=int(3 * scale))
    for s in (1, -1):
        fx = x2 + math.cos(ang + s * 0.5) * 22 * scale
        fy = y2 + math.sin(ang + s * 0.5) * 22 * scale
        d.line([(x2, y2), (fx, fy)], fill=WHITE, width=int(6 * scale))

def draw_bunker(base, x, y, w, h, tint=(255, 255, 255)):
    d = ImageDraw.Draw(base)
    d.rounded_rectangle([x - w / 2, y - h, x + w / 2, y], radius=min(w, h) / 2.4,
                        fill=mix(tint, (235, 235, 245), 0.3), outline=(160, 160, 180), width=5)
    d.rounded_rectangle([x - w / 2 + 14, y - h + 12, x + w / 2 - 14, y - h * 0.45],
                        radius=30, fill=mix(tint, WHITE, 0.55))
    d.arc([x - w / 2 + 20, y - h * 0.75, x + w / 2 - 20, y + h * 0.2], 200, 340,
          fill=(170, 170, 190), width=4)

def draw_target(base, x, y, s=1.0, fallen=0.0, hi=False):
    """立式箭靶。fallen 0-1 倒下角度。"""
    spr = Image.new("RGBA", (int(260 * s), int(300 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(spr)
    cx, gy = spr.width // 2, int(280 * s)
    d.rounded_rectangle([cx - 10 * s, int(120 * s), cx + 10 * s, gy], 8, fill=(120, 90, 60))
    d.ellipse([cx - 10 * s - 16 * s, gy - 14 * s, cx + 10 * s + 16 * s, gy + 10 * s], fill=(90, 70, 50))
    rings = [WHITE, RED, WHITE, (255, 200, 40), RED]
    R = 110 * s
    cy = 110 * s
    for i, c in enumerate(rings):
        r = R * (1 - i * 0.19)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c, outline=INK, width=int(3 * s))
    if hi:
        d.ellipse([cx - R - 10, cy - R - 10, cx + R + 10, cy + R + 10], outline=(255, 235, 90), width=10)
    rot = fallen * 88
    if rot: spr = spr.rotate(-rot, expand=False)
    base.alpha_composite(spr, (int(x - spr.width / 2), int(y - spr.height)))

def glow(base, x, y, r, color, alpha=160):
    g = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    for i in range(8, 0, -1):
        rr = r * i / 8
        gd.ellipse([r - rr, r - rr, r + rr, r + rr], fill=color + (int(alpha * (1 - i / 9)),))
    base.alpha_composite(g, (int(x - r), int(y - r)))

def burst(base, x, y, t01, color, n=14, seed=7, scale=1.0):
    """命中爆裂粒子 t01: 0->1"""
    if t01 <= 0 or t01 >= 1.4: return
    rnd = random.Random(seed)
    d = ImageDraw.Draw(base)
    for i in range(n):
        ang = rnd.uniform(0, math.tau)
        sp = rnd.uniform(120, 420) * scale
        life = rnd.uniform(0.5, 1.0)
        p = min(1.0, t01 / life)
        if p >= 1: continue
        px = x + math.cos(ang) * sp * p
        py = y + math.sin(ang) * sp * p + 260 * p * p
        r = max(2, 10 * (1 - p)) * scale
        c = mix(color, WHITE, rnd.random() * 0.6)
        d.ellipse([px - r, py - r, px + r, py + r], fill=c + (int(255 * (1 - p)),))

def speed_lines(base, side, t, y0=180, y1=760, n=16, seed=3):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(base)
    for i in range(n):
        y = rnd.uniform(y0, y1)
        ln = rnd.uniform(120, 420)
        x = rnd.uniform(0, CW - ln)
        a = int(70 * (0.5 + 0.5 * math.sin(t * 20 + i)))
        d.line([(x, y), (x + ln, y)], fill=(255, 255, 255, a), width=rnd.choice([3, 4, 6]))

def dust(base, x, y, t01, seed=1):
    if t01 < 0 or t01 > 1: return
    rnd = random.Random(seed)
    d = ImageDraw.Draw(base)
    for i in range(6):
        dx = rnd.uniform(-50, 50) * t01
        dy = -rnd.uniform(0, 60) * t01
        r = 8 + 16 * t01
        a = int(160 * (1 - t01))
        d.ellipse([x + dx - r, y + dy - r, x + dx + r, y + dy + r], fill=(235, 225, 205, a))

def ko_stars(base, x, y, t, seed=5):
    d = ImageDraw.Draw(base)
    for i in range(3):
        ang = t * 6 + i * 2.09
        sx = x + math.cos(ang) * 55
        sy = y + math.sin(ang) * 22 - 40
        star = text_sprite("★", 40, fill=(255, 215, 60), stroke=(120, 90, 0), sw=2)
        paste_center(base, star, sx, sy, alpha=0.9)

def confetti(base, t0, t, n=90, seed=11, top=0):
    if t < t0: return
    p = t - t0
    rnd = random.Random(seed)
    d = ImageDraw.Draw(base)
    cols = [RED, BLUE, (255, 200, 40), (80, 220, 120), (255, 120, 200), WHITE]
    for i in range(n):
        x0 = rnd.uniform(0, CW)
        vy = rnd.uniform(240, 520)
        y = top + vy * p + rnd.uniform(0, 400)
        if y > CH + 40: continue
        x = x0 + math.sin(p * 3 + i) * 60
        c = cols[i % len(cols)]
        w, h = rnd.uniform(10, 20), rnd.uniform(6, 12)
        d.rounded_rectangle([x - w, y - h, x + w, y + h], 5, fill=c + (230,))

# ---------- 场地背景（侧视） ----------
def arena_bg(img, floor_y=790, wall_top=(210, 232, 250), wall_bot=(170, 205, 240)):
    d = ImageDraw.Draw(img)
    for yy in range(0, floor_y, 4):
        k = yy / floor_y
        d.line([(0, yy), (CW, yy)], fill=mix(wall_top, wall_bot, k))
    # 窗户
    for wx in (140, 620, 1100, 1580):
        d.rounded_rectangle([wx, 120, wx + 220, 340], 22, fill=(235, 246, 255), outline=(140, 170, 200), width=6)
        d.line([(wx + 110, 126), (wx + 110, 334)], fill=(140, 170, 200), width=4)
    # 横幅
    d.rounded_rectangle([520, 70, 1400, 150], 26, fill=(50, 46, 60))
    d.text((960, 110), "ARCHERY TAG  ARENA", font=font(52), fill=(255, 220, 90), anchor="mm")
    # 地板
    for yy in range(floor_y, CH, 4):
        k = (yy - floor_y) / (CH - floor_y)
        d.line([(0, yy), (CW, yy)], fill=mix(FLOOR, FLOOR2, k))
    for lx in range(0, CW, 160):
        d.line([(lx, floor_y), (lx - 60, CH)], fill=(210, 170, 108), width=3)
    d.line([(0, floor_y), (CW, floor_y)], fill=(190, 150, 92), width=8)
    return d

def center_strip(img, floor_y=790, w=140):
    d = ImageDraw.Draw(img)
    import math as m
    for i in range(int(w * m.pi / 2)):
        pass
    d.polygon([(CW/2 - w, floor_y), (CW/2 + w, floor_y), (CW/2 + w*1.7, CH), (CW/2 - w*1.7, CH)], fill=SAFEY)
    d.line([(CW/2 - w, floor_y), (CW/2 - w*1.7, CH)], fill=(255, 235, 150), width=6)
    d.line([(CW/2 + w, floor_y), (CW/2 + w*1.7, CH)], fill=(255, 235, 150), width=6)

def floor_ellipse_shadow(img, x, y, rx, ry, alpha=70):
    sh = Image.new("RGBA", (int(rx*2), int(ry*2)), (0,0,0,0))
    sd = ImageDraw.Draw(sh)
    sd.ellipse([0, 0, rx*2, ry*2], fill=(30, 25, 40, alpha))
    img.alpha_composite(sh, (int(x - rx), int(y - ry)))

# ---------- 摄像机 ----------
def apply_cam(world, cam, shake=0.0, seed=0):
    z = cam["zoom"]
    cx, cy = cam["cx"], cam["cy"]
    if shake > 0:
        rnd = random.Random(seed)
        cx += rnd.uniform(-1, 1) * shake
        cy += rnd.uniform(-1, 1) * shake
    cw, chh = W / z, H / z
    cx = clamp(cx, cw / 2, CW - cw / 2)
    cy = clamp(cy, chh / 2, CH - chh / 2)
    frame = world.crop((int(cx - cw / 2), int(cy - chh / 2), int(cx + cw / 2), int(cy + chh / 2)))
    return frame.resize((W, H), Image.LANCZOS if z < 1.02 else Image.BILINEAR)

# ======================================================================
# 场景绘制：每个函数 draw_world(img, t, T) -> (cam dict, shake amp)
# ======================================================================

def scene1(img, t, T):
    """开场标题：全景 + 拉弓特写 + 箭飞出"""
    arena_bg(img)
    center_strip(img)
    d = ImageDraw.Draw(img)
    z = 0.92 + 0.08 * ease(t / T)
    # 队员
    for i, (x, y) in enumerate([(280, 880), (460, 900), (640, 885)]):
        floor_ellipse_shadow(img, x, y, 90, 22)
        paste_player(img, "red", x, y, "stand", t + i, facing=1)
    for i, (x, y) in enumerate([(1640, 880), (1460, 900), (1280, 885)]):
        floor_ellipse_shadow(img, x, y, 90, 22)
        paste_player(img, "blue", x, y, "stand", t + i + 0.3, facing=-1)
    for bx, by, tw in [(540, 900, (255, 150, 150)), (1380, 900, (150, 180, 255))]:
        draw_bunker(img, bx, by, 300, 210, tint=tw)
    # 中央红队射手拉弓（特写目标）
    sx, sy = 880, 920
    floor_ellipse_shadow(img, sx, sy, 100, 24)
    if t < 3.4:
        paste_player(img, "red", sx, sy, "shoot", t * 0.5, facing=1)
    else:
        paste_player(img, "red", sx, sy, "stand", t, facing=1)
        # 箭飞出
        ft = t - 3.4
        ax = sx + 160 + ft * 1500
        ay = 700 - ft * 60
        if ax < CW + 200:
            draw_arrow_fx(img, ax, ay, -0.04, "red", trail=7, scale=1.4)
            if t > 3.35 and t < 3.5:
                glow(img, sx + 150, sy - 220, 130, (255, 240, 120), 130)
    # 弓弦音效感：拉弓时镜头推近
    if 2.2 < t < 3.6:
        z += 0.28 * ease((t - 2.2) / 1.4)
    cam = dict(cx=CW/2, cy=620, zoom=z)
    shake = 10 * max(0, 1 - abs(t - 3.45) / 0.3)
    return cam, shake

def scene2(img, t, T):
    """俯视规则图：红区/蓝区/安全区 + 装备"""
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, CW, CH], fill=(46, 44, 66))
    # 俯视场地
    cx0, cy0, cw_, ch_ = CW/2, 390, 1500, 500
    box = [cx0 - cw_/2, cy0 - ch_/2, cx0 + cw_/2, cy0 + ch_/2]
    d.rounded_rectangle(box, 40, fill=(70, 66, 92))
    half = cw_/2
    d.rounded_rectangle([box[0]+8, box[1]+8, cx0 - 6, box[3]-8], 30, fill=mix(RED, WHITE, 0.82))
    d.rounded_rectangle([cx0 + 6, box[1]+8, box[2]-8, box[3]-8], 30, fill=mix(BLUE, WHITE, 0.82))
    d.rounded_rectangle([cx0 - 95, box[1]+8, cx0 + 95, box[3]-8], 30, fill=mix(SAFEY, WHITE, 0.35))
    d.line([(cx0, box[1]+8), (cx0, box[3]-8)], fill=(255,255,255), width=4)
    # 中线文字
    paste_center(img, text_sprite("安 全 中 立 区", 46, fill=(120, 85, 0), stroke=None, sw=0), cx0, box[1]+56)
    paste_center(img, text_sprite("红 队", 60, fill=RED, stroke=None, sw=0), box[0]+230, cy0-60)
    paste_center(img, text_sprite("蓝 队", 60, fill=BLUE, stroke=None, sw=0), box[2]-230, cy0-60)
    # 障碍物 + 箭靶（俯视）
    rnd = random.Random(9)
    for side in (0, 1):
        sgn = 1 if side == 0 else -1
        for i in range(3):
            ox = cx0 + sgn * (160 + i * 220) + rnd.uniform(-30, 30)
            oy = box[1] + 150 + rnd.uniform(0, 90)
            d.ellipse([ox-62, oy-40, ox+62, oy+40], fill=(240, 240, 250), outline=(150,150,175), width=5)
            d.ellipse([ox-36, oy-24, ox+36, oy+24], fill=(255,255,255))
        for i in range(3):
            tx = cx0 + sgn * (300 + i * 200)
            ty = box[3] - 52
            d.ellipse([tx-32, ty-20, tx+32, ty+20], fill=WHITE, outline=INK, width=4)
            d.ellipse([tx-15, ty-9, tx+15, ty+9], fill=RED)
    # 队员标记
    for i in range(5):
        px = box[0] + 110 + i * 120; py = box[1] + 360 + (i%2)*36
        d.ellipse([px-30, py-30, px+30, py+30], fill=RED, outline=WHITE, width=5)
    for i in range(5):
        px = box[2] - 110 - i * 120; py = box[1] + 360 + (i%2)*36
        d.ellipse([px-30, py-30, px+30, py+30], fill=BLUE, outline=WHITE, width=5)
    # 装备图标行
    paste_center(img, text_sprite("装备一览", 42, fill=(255, 220, 90)), CW/2, 690)
    icons = [("反曲弓", "bow"), ("泡沫箭", "arrows"), ("护面罩", "mask"), ("护臂", "arm")]
    for i, (label, kind) in enumerate(icons):
        ix = CW/2 - 480 + i * 320
        d.rounded_rectangle([ix-130, 730, ix+130, 920], 30, fill=(62, 58, 88), outline=(120, 116, 150), width=4)
        draw_equipment_icon(d, ix, 800, kind)
        paste_center(img, text_sprite(label, 36, fill=WHITE), ix, 878)
    cam = dict(cx=CW/2, cy=CH/2 - 20, zoom=1.02 - 0.10 * ease(t / T))
    return cam, 0

def draw_equipment_icon(d, x, y, kind):
    if kind == "bow":
        d.arc([x-20, y-64, x+76, y+64], 80, 280, fill=(200, 150, 90), width=12)
        d.line([(x+28, y-58), (x-30, y), (x+28, y+58)], fill=WHITE, width=4)
        d.line([(x-30, y), (x+66, y)], fill=(96, 66, 42), width=8)
        d.ellipse([x+58, y-12, x+82, y+12], fill=(90, 60, 220))
    elif kind == "arrows":
        for i, dy in enumerate((-26, 0, 26)):
            d.line([(x-60, y+dy), (x+40, y+dy)], fill=(96, 66, 42), width=8)
            d.ellipse([x+34, y+dy-12, x+58, y+dy+12], fill=[RED, BLUE, (255,200,40)][i], outline=INK, width=2)
            d.line([(x-60, y+dy-8), (x-76, y+dy), (x-60, y+dy+8)], fill=WHITE, width=4)
    elif kind == "mask":
        d.ellipse([x-56, y-52, x+56, y+52], fill=(70, 68, 80), outline=INK, width=5)
        d.rounded_rectangle([x-44, y-30, x+44, y+18], 18, fill=(30, 30, 40))
        d.ellipse([x-30, y-24, x-6, y-6], fill=(160, 200, 255))
    elif kind == "arm":
        d.rounded_rectangle([x-24, y-64, x+30, y+64], 26, fill=(60, 180, 120), outline=INK, width=4)
        for i in range(3):
            d.line([(x-24, y-30+i*30), (x+30, y-30+i*30)], fill=(40, 140, 92), width=6)

def scene3(img, t, T):
    """开局冲刺：两队冲向中线抢箭"""
    arena_bg(img)
    center_strip(img)
    speed_lines(img, 0, t)
    p = ease(t / T)
    # 中央散落的箭
    d = ImageDraw.Draw(img)
    rnd = random.Random(4)
    for i in range(6):
        ax = CW/2 + rnd.uniform(-140, 140); ay = 860 + rnd.uniform(-20, 40)
        ang = rnd.uniform(-0.4, 0.4)
        x2, y2 = ax - math.cos(ang)*40, ay - math.sin(ang)*40
        d.line([(ax, ay), (x2, y2)], fill=(96, 66, 42), width=8)
        d.ellipse([ax-11, ay-11, ax+11, ay+11], fill=[RED, BLUE][i % 2], outline=INK, width=3)
    redx = lerp_list([(-80, 240, 640, 700), (760, 660)], p)
    for i in range(4):
        px = 180 + i * 150 + p * 520
        py = 850 + (i % 2) * 60 + math.sin(t * 9 + i) * 6
        floor_ellipse_shadow(img, px, py, 84, 20)
        paste_player(img, "red", px, py, "run", t + i * 0.3, facing=1)
        dust(img, px - 60, py - 6, (t * 2 + i) % 1.0, seed=i + 2)
    for i in range(4):
        px = CW - 180 - i * 150 - p * 520
        py = 850 + (i % 2) * 60 + math.sin(t * 9 + i + 1) * 6
        floor_ellipse_shadow(img, px, py, 84, 20)
        paste_player(img, "blue", px, py, "run", t + i * 0.27, facing=-1)
        dust(img, px + 60, py - 6, (t * 2 + i) % 1.0, seed=i + 9)
    cam = dict(cx=CW/2, cy=620, zoom=0.94 + 0.06 * math.sin(t * 2.2))
    return cam, 0

def lerp_list(pairs, p):
    seg = p * (len(pairs) - 1)
    i = min(int(seg), len(pairs) - 2)
    k = seg - i
    return pairs[i][0] + (pairs[i + 1][0] - pairs[i][0]) * k, pairs[i][1] + (pairs[i + 1][1] - pairs[i][1]) * k

def scene4(img, t, T):
    """激烈攻防：射箭/闪避/接箭复活/出局"""
    arena_bg(img)
    center_strip(img)
    shake = 0
    # ---- 左：红队射手 + 掩体 ----
    draw_bunker(img, 470, 900, 320, 230, tint=(255, 150, 150))
    r_shoot1 = 20.6
    if t < 1.6:  # 拉弓
        paste_player(img, "red", 330, 905, "shoot", t * 0.7, facing=1)
    else:
        paste_player(img, "red", 330, 905, "stand", t, facing=1)
    # 箭1：飞向蓝队 → 闪避
    if t > 1.6 and t < 3.0:
        p = (t - 1.6) / 1.4
        ax = 470 + p * 740
        ay = 660 - math.sin(p * math.pi) * 40
        draw_arrow_fx(img, ax, ay, 0.0, "red", trail=6)
    # 蓝队闪避
    b1x, b1y = 1260, 880
    dodge = 1.9 < t < 2.9
    floor_ellipse_shadow(img, b1x, b1y, 90, 22)
    paste_player(img, "blue", b1x, b1y, "dodge" if dodge else "stand", t, facing=-1)
    if dodge:
        paste_center(img, text_sprite("闪!", 52, fill=(90, 200, 255)), b1x, b1y - 260 - ease((t-1.9)/0.3) * 20, rot=8)
    # ---- 箭2：被蓝队接住 → 复活 ----
    catch_t = 4.9
    if 3.8 <= t < catch_t + 0.05:
        p = (t - 3.8) / (catch_t - 3.8)
        ax = 470 + p * (b1x - 60 - 470)
        ay = 640 + p * (b1y - 160 - 640)
        draw_arrow_fx(img, ax, ay, 0.0, "red", trail=6)
    if catch_t <= t < catch_t + 0.5:
        glow(img, b1x - 40, b1y - 170, 170, (120, 230, 255), 200)
    if catch_t <= t < catch_t + 1.2:
        paste_center(img, text_sprite("接住了！", 62, fill=(120, 230, 255)), b1x, b1y - 330, scale=pop_scale(t, catch_t, 0.4))
    # 出局蓝队员躺地 → 复活站起
    dead_x, dead_y = 1050, 905
    rev_t = 5.7
    if t < rev_t:
        floor_ellipse_shadow(img, dead_x, dead_y, 110, 24)
        paste_player(img, "blue", dead_x, dead_y, "stand", 0, facing=-1, bow=False, rot=86, alpha=0.75)
        ko_stars(img, dead_x, dead_y - 190, t)
    else:
        rp = ease((t - rev_t) / 0.8)
        if rp < 1:
            glow(img, dead_x, dead_y - 150, 150 + 60 * (1 - rp), (255, 240, 130), 170)
            paste_center(img, text_sprite("复活！", 58, fill=(255, 240, 130)), dead_x, dead_y - 330, scale=pop_scale(t, rev_t, 0.4))
        paste_player(img, "blue", dead_x, dead_y - (1 - rp) * 40, "cheer" if rp >= 1 else "stand", t, facing=-1, bow=False)
        for i in range(3):
            ang = t * 5 + i * 2.1
            d = ImageDraw.Draw(img)
            sx = dead_x + math.cos(ang) * 70 * rp
            sy = dead_y - 120 + math.sin(ang) * 40 * rp - rp * 60
            d.ellipse([sx-6, sy-6, sx+6, sy+6], fill=(255, 240, 130, 220))
    # ---- 箭3：蓝队反击 → 红队出局 ----
    hit_t = 9.6
    if 8.4 <= t < hit_t + 0.05:
        p = (t - 8.4) / (hit_t - 8.4)
        ax = b1x - 60 - p * (b1x - 60 - 560)
        ay = b1y - 200 + p * (640 - (b1y - 200))
        draw_arrow_fx(img, ax, ay, math.pi, "blue", trail=6)
    if hit_t <= t < hit_t + 0.6:
        glow(img, 560, 740, 160, (255, 120, 110), 200)
        shake = 14
    if hit_t <= t < hit_t + 1.0:
        paste_center(img, text_sprite("出局！", 66, fill=(255, 100, 90)), 560, 560, scale=pop_scale(t, hit_t, 0.4), rot=-6)
    if t >= hit_t:
        paste_player(img, "red", 560, 905, "stand", 0, facing=1, bow=False, rot=86, alpha=0.85)
        ko_stars(img, 560, 700, t - hit_t)
    elif t > 6.5:
        paste_player(img, "red", 560, 905, "stand", t, facing=1)
    # 右侧其他蓝队员
    for i, bx in enumerate((1440, 1590)):
        floor_ellipse_shadow(img, bx, 890 + i * 20, 84, 20)
        paste_player(img, "blue", bx, 890 + i * 20, "stand", t + i, facing=-1, bow=(i == 1))
    cam = dict(cx=880, cy=600, zoom=1.0 + 0.04 * math.sin(t * 1.6))
    return cam, shake * max(0, 1 - (t - hit_t) / 0.4) if t >= hit_t else 0

def scene5(img, t, T):
    """攻击箭靶：三连射逐一击落"""
    arena_bg(img)
    center_strip(img)
    hit_times = [1.4, 3.3, 5.2]
    # 箭靶在右侧（蓝方后场）
    txs = [1000, 1250, 1500]
    fallen = [max(0.0, min(1.0, (t - (ht + 0.12)) / 0.5)) for ht in hit_times]
    for i, tx in enumerate(txs):
        draw_target(img, tx, 900, 1.05, fallen[i], hi=(t < hit_times[i] and t > hit_times[i] - 0.8 and i == 0))
    # 红队射手
    st = 0.4
    phase = "shoot" if any(0 <= t - (ht - 1.2) < 1.2 for ht in hit_times) else "stand"
    paste_player(img, "red", 340, 920, phase, (t * 0.8) % 1.2, facing=1)
    # 三支箭飞行
    d = ImageDraw.Draw(img)
    for i, ht in enumerate(hit_times):
        st0 = ht - 1.2
        if st0 <= t < ht + 0.1:
            p = (t - st0) / 1.2
            ax = 470 + p * (txs[i] - 470)
            ay = 700 + p * (690 - 700) - math.sin(p * math.pi) * 60
            draw_arrow_fx(img, ax, ay, 0.0, "red", trail=7, scale=1.2)
        if ht <= t < ht + 0.7:
            burst(img, txs[i], 700, (t - ht) / 0.55, (255, 200, 60), seed=i + 3, scale=1.2)
            glow(img, txs[i], 700, 140, (255, 220, 90), 150)
    if t > hit_times[2] + 0.3:
        paste_center(img, text_sprite("全部击落！", 60, fill=(255, 215, 60)), CW/2 + 300, 420, scale=pop_scale(t, hit_times[2] + 0.3, 0.4))
        confetti(img, hit_times[2] + 0.3, t, n=60, seed=21, top=200)
    cam = dict(cx=940, cy=600, zoom=1.02 + 0.10 * ease(t / T))
    return cam, 0

def scene6(img, t, T):
    """高潮决胜：交错对射 + 慢动作 + 一箭定胜负"""
    arena_bg(img)
    center_strip(img)
    slow = 4.6 <= t < 7.6
    # 对峙二人
    rx, ry = 560, 910
    bx, by = 1360, 910
    floor_ellipse_shadow(img, rx, ry, 100, 24)
    floor_ellipse_shadow(img, bx, by, 100, 24)
    paste_player(img, "red", rx, ry, "shoot", t * 0.4, facing=1)
    paste_player(img, "blue", bx, by, "shoot", t * 0.4 + 0.2, facing=-1)
    # 交错箭（慢动作拉长拖尾）
    d = ImageDraw.Draw(img)
    if t < 4.6:
        for k, (team, sign) in enumerate((("red", 1), ("blue", -1))):
            p = (t * 0.9 + k * 0.35) % 1.0
            ax = rx + sign * p * (bx - rx)
            ay = 700 - math.sin(p * math.pi) * 90 - k * 40
            draw_arrow_fx(img, ax, ay, 0 if sign > 0 else math.pi, team, trail=8)
    else:
        # 慢动作两支箭停在空中
        for k, (team, sign, yy) in enumerate((("red", 1, 640), ("blue", -1, 720))):
            p = clamp((t - 4.6) * 0.25, 0, 1)
            ax = rx + sign * (120 + p * 480)
            draw_arrow_fx(img, ax, yy, 0 if sign > 0 else math.pi, team, trail=10, scale=1.25)
        paste_center(img, text_sprite("慢动作!", 48, fill=(200, 220, 255)), 560, 240, rot=-8, alpha=0.85)
    # 最后一靶命中
    hit_t = 8.0
    tx = 1420
    fallen = max(0.0, min(1.0, (t - hit_t - 0.1) / 0.5)) if t > hit_t else 0.0
    draw_target(img, tx, 900, 1.1, fallen)
    if 6.8 <= t < hit_t + 0.1:
        p = (t - 6.8) / (hit_t - 6.8)
        ax = rx + p * (tx - rx)
        ay = 660 - math.sin(p * math.pi) * 50 + p * 30
        draw_arrow_fx(img, ax, ay, 0.05, "red", trail=9, scale=1.3)
    if hit_t <= t < hit_t + 0.7:
        glow(img, tx, 690, 220, (255, 240, 130), 230)
        burst(img, tx, 690, (t - hit_t) / 0.55, (255, 215, 60), n=22, scale=1.6)
    # 胜利文字 + 欢呼
    if t >= hit_t + 0.35:
        paste_center(img, text_sprite("胜 利 ！", 190, fill=(255, 215, 60), stroke=(120, 60, 0), sw=10),
                     CW/2, 430, scale=pop_scale(t, hit_t + 0.35, 0.5))
        confetti(img, hit_t + 0.35, t, n=110, seed=33)
        for i, px in enumerate((430, 630, 830)):
            paste_player(img, "red", px, 940 + (i % 2) * 30, "cheer", t + i, facing=1, bow=False)
    cam = dict(cx=CW/2, cy=600, zoom=1.08 + (0.08 if slow else 0))
    shake = 12 if hit_t <= t < hit_t + 0.35 else 0
    return cam, shake

def scene7(img, t, T):
    """安全提示：装备特写 + 笑脸"""
    d = ImageDraw.Draw(img)
    for yy in range(0, CH, 4):
        k = yy / CH
        d.line([(0, yy), (CW, yy)], fill=mix((235, 250, 240), (180, 225, 200), k))
    paste_center(img, text_sprite("安 全 第 一", 96, fill=(60, 180, 120), stroke=None, sw=0), CW/2, 150)
    # 装备卡
    cards = [("护面罩", "mask", -360), ("护臂", "arm", 0), ("反曲弓+泡沫箭", "bowarrow", 360)]
    for label, kind, dx in cards:
        cx = CW/2 + dx
        cy = 560
        d.rounded_rectangle([cx-230, cy-260, cx+230, cy+180], 44, fill=WHITE, outline=(120, 200, 160), width=6)
        if kind == "bowarrow":
            draw_equipment_icon(d, cx - 90, cy - 60, "bow")
            draw_equipment_icon(d, cx + 60, cy - 60, "arrows")
        else:
            big = Image.new("RGBA", (200, 200), (0,0,0,0))
            bd = ImageDraw.Draw(big)
            draw_equipment_icon(bd, 100, 100, kind)
            big = big.resize((320, 320), Image.LANCZOS)
            img.alpha_composite(big, (cx - 160, cy - 220))
        paste_center(img, text_sprite(label, 46, fill=INK, stroke=None, sw=0), cx, cy + 90)
    # 笑脸小人（无面罩展示笑容）竖大拇指
    spr = player_sprite("red", "cheer", t, facing=1, bow=False, scale=1.15)
    img.alpha_composite(spr, (CW - 300, CH - spr.height - 60))
    d = ImageDraw.Draw(img)
    d.ellipse([CW - 210, 320, CW - 90, 440], fill=(255, 250, 230), outline=INK, width=5)
    d.text((CW - 150, 366), "✓", font=font(64), fill=(60, 180, 120), anchor="mm")
    # 对勾动画
    k = ease(t / T)
    d.line([(CW - 228, 300 - 20 * k), (CW - 150, 380 - 20 * k)], fill=(60, 180, 120), width=14)
    d.line([(CW - 150, 380 - 20 * k), (CW - 60, 260 - 20 * k)], fill=(60, 180, 120), width=14)
    cam = dict(cx=CW/2, cy=CH/2, zoom=1.0 + 0.04 * math.sin(t * 1.8))
    return cam, 0

def scene8(img, t, T):
    """结束画面：两队击掌 + 号召"""
    arena_bg(img)
    confetti(img, 0.2, t, n=120, seed=55)
    # 红蓝两队靠近击掌
    for i in range(3):
        px = CW/2 - 300 - i * 190 + ease(min(1, t / 1.2)) * 90
        floor_ellipse_shadow(img, px, 900 - i * 10, 92, 22)
        paste_player(img, "red", px, 900 - i * 10, "cheer" if t > 1 else "run", t + i, facing=1, bow=False)
    for i in range(3):
        px = CW/2 + 300 + i * 190 - ease(min(1, t / 1.2)) * 90
        floor_ellipse_shadow(img, px, 900 - i * 10, 92, 22)
        paste_player(img, "blue", px, 900 - i * 10, "cheer" if t > 1 else "run", t + i, facing=-1, bow=False)
    # CTA 文字
    paste_center(img, text_sprite("快来试试攻防箭！", 110, fill=(255, 215, 60), stroke=(110, 60, 0), sw=8),
                 CW/2, 330, scale=pop_scale(t, 0.5, 0.5))
    # 手绘小弓箭图形替代 emoji
    d = ImageDraw.Draw(img)
    bx, by = CW/2 + 380, 320
    d.arc([bx - 10, by - 46, bx + 50, by + 46], 75, 285, fill=(200, 150, 90), width=9)
    d.line([(bx + 20, by - 42), (bx - 18, by), (bx + 20, by + 42)], fill=WHITE, width=3)
    d.line([(bx - 18, by), (bx + 46, by)], fill=(96, 66, 42), width=6)
    d.ellipse([bx + 40, by - 8, bx + 56, by + 8], fill=RED)
    paste_center(img, text_sprite("组队来一场 · 安全第一", 56, fill=WHITE), CW/2, 470)
    cam = dict(cx=CW/2, cy=600, zoom=1.05 + 0.03 * math.sin(t * 1.5))
    return cam, 0

SCENES = [scene1, scene2, scene3, scene4, scene5, scene6, scene7, scene8]

# ---------- 字幕 ----------
SUBS = [
    (0.3,  5.0,  "来一场刺激的攻防对战吧！攻防箭——融合射箭与闪避球的团队大战！"),
    (5.2,  10.0, "场地分成两半，中间是安全区，不能从中立区射箭。"),
    (10.0, 14.8, "每人一把反曲弓和安全泡沫箭：被射中就出局，接住飞箭可复活队友！"),
    (15.2, 19.6, "比赛开始！冲到中间抢箭，回到攻击区开始对战！"),
    (20.3, 26.5, "躲！射！接箭复活！"),
    (26.5, 34.6, "利用充气掩体走位，团队配合最重要！"),
    (35.2, 44.6, "别忘了攻击对方箭靶！先把所有靶子打掉也能获胜！"),
    (45.2, 54.4, "最后关头，一箭定胜负！团队合作才是王道！"),
    (55.2, 59.6, "全程佩戴面罩护臂，安全第一，享受快乐对战！"),
    (60.3, 65.4, "想玩吗？组队来一场吧！"),
]

def wrap_sub(text, n=26):
    if len(text) <= n: return [text]
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= n and ch in "，。！？、；：":
            lines.append(cur); cur = ""
    if cur: lines.append(cur)
    return lines if len(lines) <= 2 else [text[:n], text[n:]]

def draw_subtitle(frame, gt):
    for (t0, t1, text) in SUBS:
        if t0 <= gt <= t1:
            fade = min(1.0, (gt - t0) / 0.25, (t1 - gt) / 0.25)
            a = int(235 * fade)
            lines = wrap_sub(text)
            f = font(40)
            lh = 56
            bar_h = lh * len(lines) + 34
            bar = Image.new("RGBA", (W, bar_h), (0, 0, 0, 0))
            bd = ImageDraw.Draw(bar)
            maxw = max(bd.textlength(l, font=f) for l in lines)
            bw = min(W - 80, maxw + 70)
            bd.rounded_rectangle([(W - bw) / 2, 0, (W + bw) / 2, bar_h], 24, fill=(20, 18, 28, a))
            y = 18
            for l in lines:
                bd.text((W / 2, y + lh / 2), l, font=f, fill=(255, 255, 255, a), anchor="mm")
                y += lh
            frame.alpha_composite(bar, (0, H - bar_h - 26))
            break

# ---------- 大字幕（屏幕空间叠加） ----------
def screen_overlays(frame, gt):
    # 镜头1 标题
    if gt < 5.0:
        t = gt
        sc = pop_scale(t, 0.35, 0.55)
        y = 330 - 20 * ease(min(1, t / 5))
        paste_center(frame, text_sprite("攻防箭小游戏", 150, fill=(255, 215, 60), stroke=(120, 55, 0), sw=12),
                     W / 2, y, scale=sc)
        if t > 1.0:
            paste_center(frame, text_sprite("射箭 × 闪避球 · 团队大战", 56, fill=WHITE),
                         W / 2, y + 130, alpha=min(1, (t - 1.0) / 0.4))
    # 镜头2 规则标题
    if 5.0 <= gt < 15.0:
        t = gt - 5.0
        paste_center(frame, text_sprite("规则速览", 64, fill=(255, 220, 90)), W / 2, 96,
                     scale=pop_scale(gt, 5.2, 0.4))
    # 镜头3
    if 15.0 <= gt < 20.0:
        paste_center(frame, text_sprite("开局冲刺！", 84, fill=(255, 130, 90), stroke=(90, 30, 10), sw=6),
                     W / 2, 130, scale=pop_scale(gt, 15.2, 0.4), rot=-3 + math.sin(gt * 10) * 2)
    # 镜头4
    if 20.0 <= gt < 35.0:
        paste_center(frame, text_sprite("激烈攻防", 64, fill=WHITE), W - 160, 90,
                     scale=pop_scale(gt, 20.2, 0.4))
    # 镜头5
    if 35.0 <= gt < 45.0:
        paste_center(frame, text_sprite("目标：箭靶", 64, fill=(255, 200, 60)), W - 200, 90,
                     scale=pop_scale(gt, 35.2, 0.4))
    # 镜头7
    if 55.0 <= gt < 60.0:
        pass  # scene7 自带大字

def render_frame(args):
    gi = args
    # 定位场景
    acc = 0.0
    for si, dur in enumerate(DUR):
        if gi < acc + dur * FPS:
            local = (gi - acc) / FPS
            break
        acc += dur * FPS
    else:
        local = 0; si = len(DUR) - 1
    world = Image.new("RGBA", (CW, CH), (0, 0, 0, 255))
    cam, shake = SCENES[si](world, local, DUR[si])
    frame = apply_cam(world, cam, shake, seed=gi).convert("RGBA")
    gt = gi / FPS
    screen_overlays(frame, gt)
    draw_subtitle(frame, gt)
    # 结尾淡出
    if gt > TOTAL - 0.8:
        k = (gt - (TOTAL - 0.8)) / 0.8
        frame = Image.blend(frame, Image.new("RGBA", (W, H), (10, 8, 16, 255)), ease(k) * 0.95)
    return gi, frame

# ---------- 渲染帧 ----------
def render_frames():
    os.makedirs(FRAMES, exist_ok=True)
    from multiprocessing import Pool
    total = int(TOTAL * FPS)
    done = 0
    with Pool(8) as pool:
        for gi, frame in pool.imap_unordered(render_frame, range(total), chunksize=16):
            frame.convert("RGB").save(os.path.join(FRAMES, f"f_{gi:05d}.jpg"), quality=88)
            done += 1
            if done % 300 == 0:
                print(f"frames {done}/{total}", flush=True)
    print(f"frames done: {done}", flush=True)

# ---------- 合成音频（配乐 + 音效） ----------
def synth_audio():
    os.makedirs(AUDIODIR, exist_ok=True)
    sr = 44100
    n = int(TOTAL * sr)
    t = np.arange(n) / sr
    mixl = np.zeros(n)
    bpm = 128
    beat = 60 / bpm
    # 鼓组 + 贝斯 + 琶音
    def add(sig, start):
        s = int(start * sr)
        e = min(n, s + len(sig))
        if s < n: mixl[s:e] += sig[:e - s]
    def kick():
        dur = 0.16; tt = np.arange(int(dur * sr)) / sr
        f = 130 * np.exp(-tt * 22) + 42
        return 0.9 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt * 16)
    def hat():
        dur = 0.05; tt = np.arange(int(dur * sr)) / sr
        return 0.25 * np.random.default_rng(1).standard_normal(len(tt)) * np.exp(-tt * 90)
    def snare():
        dur = 0.14; tt = np.arange(int(dur * sr)) / sr
        rng = np.random.default_rng(2)
        return 0.5 * rng.standard_normal(len(tt)) * np.exp(-tt * 26) + 0.3 * np.sin(2*np.pi*190*tt) * np.exp(-tt*30)
    def bass(freq, dur=beat*0.9):
        tt = np.arange(int(dur * sr)) / sr
        return 0.42 * (np.sin(2*np.pi*freq*tt) + 0.4*np.sin(4*np.pi*freq*tt)) * np.exp(-tt*3) * np.minimum(1, tt*80)
    def pluck(freq, dur=0.22):
        tt = np.arange(int(dur * sr)) / sr
        return 0.3 * np.sin(2*np.pi*freq*tt) * np.exp(-tt*9) * np.minimum(1, tt*200)
    # A 小调进行 Am F C G
    roots = [110.0, 87.31, 65.41, 98.0]
    bar = beat * 4
    nbars = int(TOTAL / bar) + 1
    rng = np.random.default_rng(7)
    for b in range(nbars):
        t0 = b * bar
        root = roots[b % 4]
        for k in range(4):
            if k in (0, 2): add(kick(), t0 + k * beat)
            if k in (1, 3): add(snare(), t0 + k * beat)
            add(hat(), t0 + k * beat + beat/2)
            add(hat(), t0 + k * beat + beat/4)
            add(bass(root), t0 + k * beat)
        for step in range(8):
            f = root * 2 * (2 ** ((step * 3) % 7 / 12))
            if rng.random() < 0.75:
                add(pluck(min(f, 1400)), t0 + step * beat / 2)
    # SFX：whoosh / hit / ding / fanfare
    def whoosh(dur=0.4):
        tt = np.arange(int(dur * sr)) / sr
        noise = rng2.standard_normal(len(tt))
        # 简易带通扫频：用渐变窗模拟
        env = np.sin(np.pi * tt / dur) ** 2
        swept = noise * env
        # 低通近似：差分
        out = np.convolve(swept, np.ones(24)/24, mode="same")
        return 0.5 * out
    rng2 = np.random.default_rng(5)
    def hitfx():
        dur = 0.25; tt = np.arange(int(dur*sr))/sr
        body = np.sin(2*np.pi*(160*np.exp(-tt*18)+50)*tt*6)
        noise = rng2.standard_normal(len(tt)) * np.exp(-tt*40)
        return 0.6*body*np.exp(-tt*14) + 0.35*noise
    def ding():
        dur=0.5; tt=np.arange(int(dur*sr))/sr
        return (0.4*np.sin(2*np.pi*880*tt)+0.3*np.sin(2*np.pi*1320*tt))*np.exp(-tt*5)
    def fanfare():
        notes = [(523.25,0.0),(659.25,0.15),(783.99,0.3),(1046.5,0.45)]
        out = np.zeros(int(1.6*sr)); tt_all=np.arange(int(1.6*sr))/sr
        for f,st in notes:
            tt=np.arange(int(0.8*sr))/sr
            sig=(0.35*np.sin(2*np.pi*f*tt)+0.2*np.sin(2*np.pi*f*2*tt))*np.exp(-tt*3)
            s=int(st*sr); out[s:s+len(sig)]+=sig
        return out
    sfx_events = [
        (3.45, whoosh()), (4.4, hitfx()),
        (21.9, whoosh()), (24.75, ding()), (25.9, ding()), (30.0, hitfx()),
        (36.9, whoosh()), (38.8, whoosh()), (40.7, whoosh()),
        (37.0, hitfx()), (38.9, hitfx()), (40.8, hitfx()),
        (47.5, whoosh()), (53.0, fanfare()),
        (63.0, fanfare()),
    ]
    for st, sig in sfx_events:
        add(sig, st)
    # 包络：开场淡入 / 结尾淡出
    env = np.ones(n)
    fi = int(1.0 * sr); env[:fi] = np.linspace(0, 1, fi)
    fo = int(1.6 * sr); env[-fo:] *= np.linspace(1, 0, fo)
    mixl *= env
    mixl = np.tanh(mixl * 0.9) * 0.82
    stereo = np.stack([mixl, np.roll(mixl, int(0.0004 * sr))])
    import wave
    data = (stereo.T * 32767).astype(np.int16)
    with wave.open(os.path.join(AUDIODIR, "bgm.wav"), "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(data.tobytes())
    print("bgm done", flush=True)

# ---------- 合成 MP4 ----------
def mux():
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, "gongfangjian_anim.mp4")
    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(FRAMES, "f_%05d.jpg"),
           "-i", os.path.join(AUDIODIR, "bgm.wav"),
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True, capture_output=True)
    print("mux done:", out, flush=True)

if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("audio", "all"): synth_audio()
    if mode in ("frames", "all"): render_frames()
    if mode in ("mux", "all"): mux()
