# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager

fp = font_manager.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
try:
    bold_fp = font_manager.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
except Exception:
    bold_fp = fp

fig, ax = plt.subplots(figsize=(17, 12), dpi=200)
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis('off')

C_BOARD = '#1F4E79'; C_GM = '#2E75B6'; C_DEPT = '#4472C4'; C_POS = '#EDF2FA'
C_DASH = '#C55A11'; C_COMMIT = '#E2EFDA'

def box(x, y, w, h, text, fc, ec, tc, fs=10.5, bold=False, dashed=False, lw=1.2):
    b = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.12,rounding_size=0.35',
                       fc=fc, ec=ec, lw=lw, linestyle='--' if dashed else '-',
                       mutation_aspect=1)
    ax.add_patch(b)
    ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=fs,
            color=tc, fontproperties=(bold_fp if bold else fp),
            fontweight='bold' if bold else 'normal')
    return (x, y, w, h)

def line(x1, y1, x2, y2, color='#7F7F7F', dashed=False, lw=1.2):
    ax.plot([x1, x2], [y1, y2], color=color, lw=lw,
            linestyle='--' if dashed else '-', solid_capstyle='round', zorder=0)

# ---- Top governance ----
box(44, 93.4, 12, 4.2, '股东会', C_BOARD, 'white', 'white', 12, True)
box(44, 86.6, 12, 4.2, '董事会', C_BOARD, 'white', 'white', 12, True)
line(50, 93.4, 50, 90.8)

# Committees (innovative governance)
box(18, 86.6, 20, 4.2, '审计与合规委员会', C_COMMIT, '#70AD47', '#375623', 10, dashed=True)
box(62, 86.6, 20, 4.2, '战略与提名薪酬委员会', C_COMMIT, '#70AD47', '#375623', 10, dashed=True)
line(44, 88.7, 38, 88.7, '#70AD47', dashed=True)
line(56, 88.7, 62, 88.7, '#70AD47', dashed=True)

# GM
box(44, 79.0, 12, 4.2, '总经理', C_GM, 'white', 'white', 12, True)
line(50, 86.6, 50, 83.2)

# Board office (securities / IPO) - dashed supervisory link
box(66, 79.0, 22, 4.2, '董事会办公室（证券事务部）', C_COMMIT, '#70AD47', '#375623', 10, dashed=True)
line(66, 88.7, 77, 88.7, '#70AD47', dashed=True)
line(77, 88.7, 77, 83.2, '#70AD47', dashed=True)
ax.text(78.2, 85.9, '上市筹备与信息披露指导', fontsize=8.5, color='#375623',
        fontproperties=fp, ha='left', va='center')

# Cross-functional product committee (matrix, innovative)
box(6, 71.5, 88, 4.2, '产品项目委员会（跨部门矩阵协作：研发—生产—质量—销售联动 · 项目负责人制）',
    '#FFF2CC', '#BF9000', '#7F6000', 10.5, dashed=True)
line(50, 79.0, 50, 75.7, '#BF9000', dashed=True)

# ---- Departments row ----
dept_y = 63.5; dept_h = 4.6; dept_w = 13.6
xs = [4.5, 20.4, 36.3, 52.2, 68.1, 84.0]
labels = ['研发中心', '生产制造部', '质量管理部', '市场销售部', '财务部', '综合管理部']
buses = [x + dept_w/2 for x in xs]
# bus line under committee
for bx in buses:
    line(50, 71.5, bx, 71.5, '#BF9000', dashed=True, lw=1.0)
    line(bx, 71.5, bx, dept_y + dept_h, '#BF9000', dashed=True, lw=1.0)
for x, lab in zip(xs, labels):
    solid = lab != '质量管理部'
    box(x, dept_y, dept_w, dept_h, lab, C_DEPT, 'white', 'white', 11.5, True)

# ---- Positions ----
positions = {
    '研发中心': ['研发总监\n（兼总工程师）', '研发工程师 ×2', '注册专员'],
    '生产制造部': ['生产经理', '生产技术员 ×3', '供应链专员'],
    '质量管理部': ['质量经理\n（管理者代表）', '质量工程师\n（QA/QC）'],
    '市场销售部': ['销售总监', '销售代表 ×2', '售后服务工程师'],
    '财务部': ['财务经理', '会计\n（兼出纳）'],
    '综合管理部': ['董事会秘书', '人事行政专员'],
}
py0 = 60.0; ph = 3.9; pw = 13.6; gap = 0.9
for x, lab in zip(xs, labels):
    cx = x + pw/2
    line(cx, dept_y, cx, py0, '#7F7F7F')
    yy = py0
    for t in positions[lab]:
        box(x, yy - ph, pw, ph, t, C_POS, '#4472C4', '#1F3864', 9.5)
        yy -= (ph + gap)

# headcount note
ax.text(50, 3.2, '定员 20 人：总经理 1 · 董事会秘书 1 · 研发 4 · 生产 5 · 质量 2 · 销售 4 · 财务 2 · 人事行政 1',
        ha='center', fontsize=10.5, color='#1F4E79', fontproperties=bold_fp)

plt.tight_layout(pad=0.4)
plt.savefig('/workspace/tmp/org_chart.png', bbox_inches='tight', facecolor='white')
print('saved')
