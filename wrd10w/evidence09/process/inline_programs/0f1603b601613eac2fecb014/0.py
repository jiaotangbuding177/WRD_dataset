# -*- coding: utf-8 -*-
"""Render 36 slides (3840x2160) from the fixed per-page text."""
import asyncio, math
from playwright.async_api import async_playwright

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:3840px; height:2160px; overflow:hidden; }
body {
  font-family: 'Noto Sans CJK SC','Noto Sans SC',sans-serif;
  background: linear-gradient(160deg,#ffffff 0%,#f5f8fc 60%,#eef4fa 100%);
  color:#0b2a5b; position:relative;
}
.slide { position:absolute; inset:0; padding:140px 160px; display:flex; flex-direction:column; }
.grad-text { background:linear-gradient(90deg,#0b2a5b 0%,#1656d6 55%,#00b8cf 100%);
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.accent { background:linear-gradient(90deg,#1656d6,#00b8cf); }
.bar { width:180px; height:14px; border-radius:7px; }
.corner { position:absolute; right:120px; top:110px; width:520px; height:520px; opacity:.10; }
.center { justify-content:center; align-items:center; text-align:center; }
.statement .big { font-size:110px; font-weight:700; line-height:1.55; }
.statement .mid { font-size:88px; font-weight:600; line-height:1.6; color:#1656d6; }
.statement .small { font-size:60px; font-weight:500; color:#3a5578; line-height:1.7; }
.chiprow { display:flex; gap:28px; justify-content:center; margin-top:90px; flex-wrap:wrap; }
.chip { border:3px solid #cfe0f2; border-radius:60px; padding:20px 44px; font-size:52px;
  font-weight:600; color:#1656d6; background:#ffffff; }
.chapter { justify-content:center; }
.chapter .num { font-size:300px; font-weight:800; line-height:1; }
.chapter .title { font-size:120px; font-weight:800; margin:40px 0 70px; line-height:1.3; }
.chapter .sub { font-size:64px; color:#3a5578; line-height:1.8; }
.grid { display:grid; gap:44px; margin-top:110px; }
.card { background:#ffffff; border:3px solid #dde8f4; border-radius:32px;
  box-shadow:0 14px 40px rgba(11,42,91,.06); display:flex; align-items:center; justify-content:center;
  font-size:66px; font-weight:700; color:#0b2a5b; padding:30px; text-align:center;
  border-top:10px solid; border-image:linear-gradient(90deg,#1656d6,#00b8cf) 1; }
.rows { display:flex; flex-direction:column; gap:56px; margin-top:120px; }
.row { display:flex; align-items:center; justify-content:center; gap:50px; }
.row .box { background:#fff; border:3px solid #dde8f4; border-radius:28px; padding:36px 60px;
  font-size:60px; font-weight:700; min-width:640px; text-align:center; }
.row .box.b { border-color:#bfe9ef; background:#f2fbfd; color:#0f7c8c; }
.row .arrow { font-size:70px; color:#00b8cf; font-weight:800; }
.chain { display:flex; flex-direction:column; align-items:center; gap:26px; margin-top:80px; }
.chain .node { background:#fff; border:3px solid #dde8f4; border-radius:26px; padding:30px 80px;
  font-size:62px; font-weight:700; }
.chain .node.last { border-color:#bfe9ef; background:linear-gradient(90deg,#eaf6fd,#f0fbfd); color:#0f7c8c; }
.chain .dn { font-size:56px; color:#00b8cf; font-weight:800; line-height:1; }
.ab { display:flex; gap:90px; margin-top:130px; justify-content:center; }
.ab .opt { width:880px; border-radius:36px; padding:70px 60px; text-align:center; font-size:64px;
  font-weight:700; background:#fff; border:3px solid #dde8f4; }
.ab .opt .tag { display:inline-block; font-size:54px; margin-bottom:30px; }
.ab .opt.b { border-color:#bfe9ef; background:#f2fbfd; }
.ab .opt.b .tag { color:#0f7c8c; }
.ab .opt.a .tag { color:#1656d6; }
.venn { position:relative; margin:120px auto 0; }
.vc { position:absolute; width:1000px; height:1000px; border-radius:50%; display:flex;
  align-items:center; justify-content:center; text-align:center; font-size:54px; font-weight:700;
  color:#123a6e; padding:120px; line-height:1.4; }
.vcenter { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); border-radius:50%;
  display:flex; align-items:center; justify-content:center; font-weight:800;
  color:#fff; text-align:center; line-height:1.4; }
.matrixwrap { display:flex; margin-top:100px; align-items:center; gap:40px; }
.yaxis { writing-mode:vertical-rl; transform:rotate(180deg); font-size:52px; font-weight:700; color:#3a5578; }
.matrix { display:grid; grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr; gap:24px;
  width:2300px; height:1400px; }
.quad { border-radius:30px; display:flex; align-items:center; justify-content:center; font-size:64px;
  font-weight:700; background:#fff; border:3px solid #dde8f4; color:#3a5578; }
.quad.hot { background:linear-gradient(135deg,#1656d6,#00b8cf); color:#fff; border:none; }
.xaxis { font-size:52px; font-weight:700; color:#3a5578; text-align:center; margin-top:30px; }
.pyr { display:flex; flex-direction:column; align-items:center; gap:22px; margin-top:90px; }
.pyr .layer { height:210px; border-radius:22px; display:flex; align-items:center; justify-content:center;
  color:#fff; font-size:62px; font-weight:700; }
.ladder { display:flex; align-items:flex-end; gap:70px; margin-top:120px; height:1250px; justify-content:center; }
.step { width:900px; border-radius:30px 30px 0 0; background:#fff; border:3px solid #dde8f4;
  border-bottom:12px solid; border-image:linear-gradient(90deg,#1656d6,#00b8cf) 1;
  display:flex; flex-direction:column; align-items:center; padding-top:60px; font-size:66px; font-weight:800; }
.step .cap { font-size:48px; font-weight:600; color:#3a5578; margin-top:34px; }
.tl { display:flex; gap:60px; margin-top:140px; width:100%; }
.tl .ph { flex:1; background:#fff; border:3px solid #dde8f4; border-radius:34px; padding:70px 60px;
  border-top:12px solid; border-image:linear-gradient(90deg,#1656d6,#00b8cf) 1; }
.tl .days { font-size:76px; font-weight:800; margin-bottom:36px; }
.tl .what { font-size:60px; font-weight:700; color:#1656d6; line-height:1.5; }
.loopwrap { position:relative; margin:60px auto 0; }
.loopwrap .ring { position:absolute; border:6px dashed #bfe9ef; border-radius:50%; }
.lnode { position:absolute; padding:34px 20px; background:#fff; border:3px solid #dde8f4;
  border-radius:26px; text-align:center; font-size:56px; font-weight:700; transform:translate(-50%,-50%); }
.lcenter { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
  border-radius:50%; background:linear-gradient(135deg,#1656d6,#00b8cf);
  color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; }
.conwrap { display:flex; align-items:center; justify-content:center; }
.rings { position:relative; width:1500px; height:1400px; }
.ring { position:absolute; border-radius:50%; display:flex; align-items:flex-start; justify-content:center; }
.golden { margin-top:70px; font-size:56px; font-weight:700; color:#0f7c8c; text-align:center;
  background:#f2fbfd; border:3px solid #bfe9ef; border-radius:26px; padding:40px; }
.quiz { display:flex; gap:90px; margin-top:90px; width:100%; }
.qs { flex:1.4; display:flex; flex-direction:column; gap:40px; }
.q { background:#fff; border:3px solid #dde8f4; border-radius:24px; padding:34px 44px; font-size:50px;
  font-weight:600; display:flex; justify-content:space-between; align-items:center; gap:30px; }
.q .sc { color:#9db2c9; font-size:44px; font-weight:700; white-space:nowrap; }
.levels { flex:1; display:flex; flex-direction:column; gap:30px; justify-content:center; }
.lv { border-radius:22px; padding:36px 44px; font-size:52px; font-weight:700; background:#fff;
  border:3px solid #dde8f4; color:#3a5578; }
.lv.hot { background:linear-gradient(90deg,#1656d6,#00b8cf); color:#fff; border:none; }
.lvhead { font-size:54px; font-weight:800; color:#1656d6; }
.closing .blk { margin:0 0 90px; }
.closing .l1 { font-size:84px; font-weight:700; line-height:1.6; }
.closing .l1 b { color:#1656d6; }
.closing .final { font-size:70px; font-weight:800; margin-top:40px; }
"""

def shell(body):
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"

def corner_svg():
    return "<svg class='corner' viewBox='0 0 100 100'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#1656d6'/><stop offset='1' stop-color='#00b8cf'/></linearGradient></defs><circle cx='30' cy='30' r='22' fill='none' stroke='url(#g)' stroke-width='2'/><circle cx='70' cy='45' r='26' fill='none' stroke='url(#g)' stroke-width='2'/><circle cx='45' cy='75' r='18' fill='none' stroke='url(#g)' stroke-width='2'/><line x1='30' y1='30' x2='70' y2='45' stroke='url(#g)' stroke-width='2'/><line x1='70' y1='45' x2='45' y2='75' stroke='url(#g)' stroke-width='2'/></svg>"

PAGES = {}
def P(n, body): PAGES[n] = shell(body)

P(1, f"""<div class='slide' style='justify-content:center;'>{corner_svg()}
<div style='max-width:2100px;'>
 <div class='bar accent' style='margin-bottom:60px;'></div>
 <div class='grad-text' style='font-size:170px;font-weight:800;line-height:1.25;'>从赛道红利到AI原生</div>
 <div style='font-size:74px;font-weight:700;margin-top:60px;color:#123a6e;'>科创企业如何抓住新一轮产业机会</div>
 <div style='font-size:54px;color:#3a5578;margin-top:46px;'>从产业机会识别，到企业能力重构</div>
</div>
<div style='position:absolute;right:170px;top:50%;transform:translateY(-50%);'>
 <svg width='1100' height='900' viewBox='0 0 110 90'>
  <defs><linearGradient id='cg' x1='0' y1='0' x2='1' y2='0'><stop offset='0' stop-color='#1656d6'/><stop offset='1' stop-color='#00b8cf'/></linearGradient></defs>
  <rect x='4' y='34' width='12' height='12' rx='2' fill='none' stroke='#1656d6' stroke-width='1.4'/>
  <rect x='4' y='52' width='12' height='12' rx='2' fill='none' stroke='#1656d6' stroke-width='1.4'/>
  <circle cx='38' cy='45' r='9' fill='none' stroke='url(#cg)' stroke-width='1.6'/>
  <circle cx='60' cy='30' r='6' fill='none' stroke='url(#cg)' stroke-width='1.4'/>
  <circle cx='60' cy='60' r='6' fill='none' stroke='url(#cg)' stroke-width='1.4'/>
  <circle cx='82' cy='45' r='13' fill='url(#cg)' opacity='0.85'/>
  <line x1='16' y1='45' x2='29' y2='45' stroke='#7f9cc4' stroke-width='1.2'/>
  <line x1='47' y1='45' x2='51' y2='45' stroke='#7f9cc4' stroke-width='1.2'/>
  <line x1='60' y1='36' x2='60' y2='39' stroke='#7f9cc4' stroke-width='1.2'/>
  <line x1='60' y1='54' x2='60' y2='51' stroke='#7f9cc4' stroke-width='1.2'/>
  <line x1='69' y1='45' x2='72' y2='45' stroke='#7f9cc4' stroke-width='1.2'/>
 </svg>
</div></div>""")

P(2, """<div class='slide center statement'>
<div class='big grad-text'>如果今天重新创业，你会选择什么？</div>
<div class='ab'>
 <div class='opt a'><span class='tag'>A</span><br>最热门的赛道</div>
 <div class='opt b'><span class='tag'>B</span><br>自己真正拥有优势的方向</div>
</div></div>""")

P(3, """<div class='slide center statement'>
<div class='bar accent' style='margin:0 auto 80px;'></div>
<div class='big'>赛道红利决定企业能否起步</div>
<div class='mid' style='margin-top:40px;'>AI原生能力决定企业能走多远</div>
</div>""")

P(4, """<div class='slide chapter'>
<div class='num grad-text'>01</div>
<div class='title'>重新理解赛道红利</div>
<div class='sub'>机会不是来自“行业很热”<br>而是来自产业结构发生变化</div>
</div>""")

P(5, """<div class='slide center statement'>
<div class='big'>赛道红利不是市场规模</div>
<div class='mid' style='margin-top:40px;'>而是进入成本与成功概率发生变化</div>
</div>""")

items6 = ["政策红利","技术红利","需求红利","供给红利","要素红利","资本红利"]
cx, cy, R = 120, 60, 44
hexnodes = ""
for i,t in enumerate(items6):
    ang = math.radians(-90 + i*60)
    x, y = cx + R*math.cos(ang), cy + R*math.sin(ang)*0.85
    hexnodes += f"<svg style='position:absolute;left:0;top:0;width:100%;height:100%;' viewBox='0 0 240 120' preserveAspectRatio='none'><line x1='120' y1='60' x2='{x:.0f}' y2='{y:.0f}' stroke='#bfe9ef' stroke-width='1'/></svg>"
    hexnodes += f"<div class='lnode' style='left:{(x/240*100):.1f}%;top:{(y/120*100):.1f}%;min-width:420px;'>{t}</div>"
P(6, f"""<div class='slide'>
<div style='text-align:center;font-size:56px;font-weight:700;color:#3a5578;'>六类产业红利</div>
<div class='loopwrap' style='width:2600px;height:1750px;margin:0 auto;'>
 <div class='ring' style='inset:0;border:5px dashed #dbeef5;'></div>
 {hexnodes}
 <div class='lcenter' style='width:560px;height:560px;font-size:72px;'>产业机会</div>
</div></div>""")

P(7, """<div class='slide center statement'>
<div class='big'>单一红利只能带来热度</div>
<div class='mid' style='margin-top:40px;'>多重红利叠加才能形成窗口</div>
<div style='margin-top:90px;display:flex;justify-content:center;'>
 <div style='width:300px;height:300px;border-radius:50%;background:rgba(22,86,214,.12);'></div>
 <div style='width:300px;height:300px;border-radius:50%;background:rgba(0,184,207,.14);margin-left:-110px;'></div>
 <div style='width:300px;height:300px;border-radius:50%;background:rgba(11,42,91,.10);margin-left:-110px;'></div>
</div></div>""")

P(8, """<div class='slide center statement'>
<div class='small'>不是“新能源汽车有没有机会”</div>
<div class='big grad-text' style='margin-top:50px;'>而是“哪个具体环节正在重构”</div>
<div style='display:flex;align-items:center;gap:34px;margin-top:100px;color:#1656d6;font-weight:700;font-size:50px;'>
<span>电池材料</span><span>·</span><span>热管理</span><span>·</span><span>功率器件</span><span>·</span><span>制造设备</span><span>·</span><span>检测</span><span>·</span><span>软件</span><span>·</span><span>回收</span>
</div></div>""")

P(9, """<div class='slide'>
<div class='rows'>
 <div class='row'><div class='box'>增量市场</div><div class='arrow'>→</div><div class='box b'>存量重构</div></div>
 <div class='row'><div class='box'>单一产品</div><div class='arrow'>→</div><div class='box b'>系统解决方案</div></div>
 <div class='row'><div class='box'>技术领先</div><div class='arrow'>→</div><div class='box b'>商业闭环</div></div>
</div></div>""")

P(10, """<div class='slide center statement'>
<div class='big'>技术指标领先</div>
<div class='mid' style='margin-top:36px;'>但客户没有理由现在购买</div>
<div class='chiprow'>
 <div class='chip'>验证周期长</div><div class='chip'>预算不明确</div><div class='chip'>交付能力不足</div><div class='chip'>替代成本过高</div>
</div></div>""")

P(11, """<div class='slide center'>
<div class='grad-text' style='font-size:150px;font-weight:800;'>产业机会</div>
<div style='font-size:86px;font-weight:700;margin-top:70px;line-height:1.7;color:#0b2a5b;'>
= 技术拐点 × 需求变化 × 供给缺口 × 时间窗口</div>
<div class='chiprow' style='margin-top:110px;'>
 <div class='chip'>技术拐点</div><div class='chip'>需求变化</div><div class='chip'>供给缺口</div><div class='chip'>时间窗口</div>
</div></div>""")

P(12, """<div class='slide chapter'>
<div class='num grad-text'>02</div>
<div class='title'>如何识别真正属于自己的机会</div>
<div class='sub'>市场很大<br>不代表它是你的市场</div>
</div>""")

P(13, """<div class='slide center'>
<div style='font-size:60px;font-weight:700;color:#3a5578;'>六维机会判断模型</div>
<div class='grid' style='grid-template-columns:repeat(3,1fr);width:3100px;height:1250px;margin-top:90px;'>
 <div class='card'>需求真实性</div><div class='card'>技术成熟度</div><div class='card'>商业可达性</div>
 <div class='card'>竞争壁垒</div><div class='card'>规模化能力</div><div class='card'>团队适配度</div>
</div></div>""")

P(14, """<div class='slide center'>
<div class='venn' style='width:2200px;height:1350px;'>
 <div class='vc' style='left:0;top:0;background:rgba(22,86,214,.10);'>产业真实需求</div>
 <div class='vc' style='right:0;top:0;background:rgba(0,184,207,.12);'>团队独特能力</div>
 <div class='vc' style='left:8%;bottom:0;background:rgba(11,42,91,.08);'>技术成熟窗口</div>
 <div class='vc' style='right:8%;bottom:0;background:rgba(22,86,214,.08);'>可获得的商业资源</div>
 <div class='vcenter' style='background:linear-gradient(135deg,#1656d6,#00b8cf);width:520px;height:520px;font-size:60px;'>属于你的机会</div>
</div></div>""")

P(15, """<div class='slide'>
<div class='rows' style='gap:48px;margin-top:80px;'>
 <div class='row'><div class='box'>只有技术</div><div class='arrow'>→</div><div class='box b'>科研项目</div></div>
 <div class='row'><div class='box'>只有需求</div><div class='arrow'>→</div><div class='box b'>项目制生意</div></div>
 <div class='row'><div class='box'>没有商业资源</div><div class='arrow'>→</div><div class='box b'>无法成交</div></div>
 <div class='row'><div class='box'>没有组织能力</div><div class='arrow'>→</div><div class='box b'>订单越多越危险</div></div>
</div></div>""")

P(16, """<div class='slide center'><div class='chain'>
<div class='node'>行业</div><div class='dn'>↓</div>
<div class='node'>场景</div><div class='dn'>↓</div>
<div class='node'>流程</div><div class='dn'>↓</div>
<div class='node'>痛点</div><div class='dn'>↓</div>
<div class='node'>付费人</div><div class='dn'>↓</div>
<div class='node last'>产品</div>
</div></div>""")

P(17, """<div class='slide center'><div class='chain'>
<div class='node'>AI＋制造</div><div class='dn'>↓</div>
<div class='node'>高端装备装配与调试</div><div class='dn'>↓</div>
<div class='node'>依赖资深工程师经验</div><div class='dn'>↓</div>
<div class='node last'>工艺知识与故障诊断智能体</div>
</div></div>""")

P(18, """<div class='slide center'>
<div style='font-size:60px;font-weight:700;color:#3a5578;'>四类结构性机会</div>
<div class='grid' style='grid-template-columns:1fr 1fr;width:3000px;height:1150px;margin-top:90px;'>
 <div class='card'>关键环节国产替代</div><div class='card'>传统行业效率重构</div>
 <div class='card'>科研成果工程化</div><div class='card'>新技术催生新产品</div>
</div></div>""")

P(19, """<div class='slide center'>
<div class='matrixwrap'>
 <div class='yaxis'>市场吸引力</div>
 <div>
  <div class='matrix'>
   <div class='quad'>能力型机会</div><div class='quad hot'>优先投入</div>
   <div class='quad'>谨慎观察</div><div class='quad'>资源型机会</div>
  </div>
  <div class='xaxis'>企业适配度</div>
 </div>
</div></div>""")

P(20, """<div class='slide center statement'>
<div class='small'>不是从“做一套平台”开始</div>
<div class='big grad-text' style='margin-top:50px;'>而是从一个客户愿意付费的问题开始</div>
</div>""")

P(21, """<div class='slide chapter'>
<div class='num grad-text'>03</div>
<div class='title'>从“使用AI”走向“AI原生”</div>
<div class='sub'>不是给企业增加一个工具<br>而是重新设计企业</div>
</div>""")

P(22, """<div class='slide center'>
<div class='ladder'>
 <div class='step' style='height:760px;'>使用AI<div class='cap'>个人工具</div></div>
 <div class='step' style='height:1000px;'>AI赋能<div class='cap'>嵌入流程</div></div>
 <div class='step' style='height:1250px;background:linear-gradient(180deg,#f2fbfd,#ffffff);border-color:#bfe9ef;'>AI原生<div class='cap'>重构产品与组织</div></div>
</div></div>""")

P(23, """<div class='slide center statement'>
<div class='small'>原来的十个按钮<br>加上一个AI聊天框</div>
<div class='big grad-text' style='margin-top:60px;'>不等于AI原生</div>
</div>""")

P(24, """<div class='slide center'><div class='pyr'>
 <div class='layer' style='width:640px;background:linear-gradient(90deg,#00b8cf,#3fc9dc);'>商业模式原生</div>
 <div class='layer' style='width:940px;background:linear-gradient(90deg,#0e7fae,#00b8cf);'>产品原生</div>
 <div class='layer' style='width:1240px;background:linear-gradient(90deg,#1656d6,#1e7bd0);'>组织原生</div>
 <div class='layer' style='width:1540px;background:linear-gradient(90deg,#124a9e,#1656d6);'>流程原生</div>
 <div class='layer' style='width:1840px;background:linear-gradient(90deg,#0b2a5b,#124a9e);'>数据原生</div>
</div></div>""")

P(25, """<div class='slide center'>
<div class='chiprow' style='max-width:3200px;'>
 <div class='chip'>专业知识密度高</div><div class='chip'>研发周期长</div><div class='chip'>复合人才稀缺</div>
 <div class='chip'>经验高度依赖核心人员</div><div class='chip'>资料和数据大量分散</div>
</div>
<div style='margin-top:120px;font-size:54px;font-weight:700;color:#0f7c8c;'>知识网络连接孤立节点，形成可调用的企业知识体系</div>
</div>""")

P(26, """<div class='slide center statement'>
<div class='big'>AI不是简单替代一个人</div>
<div class='mid' style='margin-top:36px;'>而是重新拆分一组工作</div>
<div class='chiprow'>
 <div class='chip'>检索</div><div class='chip'>整理</div><div class='chip'>分析</div><div class='chip'>生成</div><div class='chip'>校验</div><div class='chip'>执行</div>
</div></div>""")

P(27, """<div class='slide center'><div class='chain'>
<div class='node'>第一阶段：帮员工写</div><div class='dn'>↓</div>
<div class='node'>第二阶段：帮团队做</div><div class='dn'>↓</div>
<div class='node last'>第三阶段：帮助企业持续学习</div>
</div></div>""")

P(28, """<div class='slide chapter'>
<div class='num grad-text'>04</div>
<div class='title'>科创企业的AI原生实践路径</div>
<div class='sub'>不要先买模型<br>先找到值得改变的工作</div>
</div>""")

P(29, """<div class='slide'>
<div style='text-align:center;font-size:56px;font-weight:700;color:#3a5578;'>首个AI场景的五个标准</div>
<div class='loopwrap' style='width:2400px;height:1600px;margin:40px auto 0;'>
 <div class='ring' style='inset:0;border:5px dashed #dbeef5;'></div>
 <div class='lnode' style='left:8%;top:45%;'>高频</div>
 <div class='lnode' style='left:28%;top:88%;'>高成本</div>
 <div class='lnode' style='left:72%;top:88%;'>有数据</div>
 <div class='lnode' style='left:92%;top:45%;'>可评价</div>
 <div class='lnode' style='left:50%;top:10%;'>可闭环</div>
 <div class='lcenter' style='width:560px;height:560px;font-size:64px;'>首个AI场景</div>
</div></div>""")

P(30, """<div class='slide center'>
<div class='tl'>
 <div class='ph'><div class='days grad-text'>0—30天</div><div class='what'>找到真实场景</div></div>
 <div class='ph'><div class='days grad-text'>31—60天</div><div class='what'>跑通最小闭环</div></div>
 <div class='ph'><div class='days grad-text'>61—90天</div><div class='what'>评估复制与扩展</div></div>
</div></div>""")

P(31, """<div class='slide'>
<div class='loopwrap' style='width:2100px;height:1650px;margin:60px auto 0;'>
 <div class='ring' style='inset:60px;'></div>
 <div class='lnode' style='left:14%;top:22%;'>资料进入</div>
 <div class='lnode' style='left:86%;top:22%;'>AI分析</div>
 <div class='lnode' style='left:86%;top:78%;'>人工复核</div>
 <div class='lnode' style='left:14%;top:78%;'>进入业务</div>
 <div class='lnode' style='left:50%;top:98%;'>结果回流</div>
 <div class='lcenter' style='width:420px;height:420px;font-size:56px;'>最小闭环</div>
</div></div>""")

P(32, """<div class='slide center'>
<div class='conwrap'>
 <div class='rings'>
  <div class='ring' style='inset:0;background:rgba(22,86,214,.06);padding-top:40px;'><span style='font-size:54px;font-weight:700;color:#3a5578;'>通用能力：采购</span></div>
  <div class='ring' style='inset:230px;background:rgba(22,86,214,.12);padding-top:40px;'><span style='font-size:54px;font-weight:700;color:#123a6e;'>行业流程：联合开发</span></div>
  <div class='ring' style='inset:470px;background:linear-gradient(135deg,#1656d6,#00b8cf);align-items:center;'><span style='font-size:58px;font-weight:800;color:#fff;'>核心壁垒：自己掌握</span></div>
 </div>
</div>
<div class='golden'>模型不一定属于你<br>但数据、流程、知识和客户必须属于你</div>
</div>""")

P(33, """<div class='slide center'>
<div style='font-size:60px;font-weight:700;color:#3a5578;'>AI原生的最小基础设施</div>
<div class='grid' style='grid-template-columns:repeat(3,1fr);width:3100px;height:1200px;margin-top:90px;'>
 <div class='card'>数据与文档</div><div class='card'>权限与安全</div><div class='card'>专业知识</div>
 <div class='card'>业务工作流</div><div class='card'>评价与反馈</div><div class='card'>审计与合规</div>
</div></div>""")

P(34, """<div class='slide center'>
<div class='chiprow' style='max-width:3300px;gap:34px;'>
 <div class='chip'>追逐所有热门赛道</div><div class='chip'>把AI当成独立部门</div><div class='chip'>先买模型再找场景</div>
 <div class='chip'>把Demo当成产品</div><div class='chip'>只算模型成本</div><div class='chip'>追求完全无人化</div>
 <div class='chip'>只提效、不沉淀</div>
</div>
<div style='margin-top:110px;font-size:56px;font-weight:800;' class='grad-text'>绕开七个常见误区，走向AI原生</div>
</div>""")

P(35, """<div class='slide'>
<div class='quiz'>
 <div class='qs'>
  <div class='q'><span>我们的客户痛点是否真实？</span><span class='sc'>0 1 2</span></div>
  <div class='q'><span>我们是否拥有独特数据与资源？</span><span class='sc'>0 1 2</span></div>
  <div class='q'><span>产品是否能够标准化复制？</span><span class='sc'>0 1 2</span></div>
  <div class='q'><span>AI是否已经进入业务流程？</span><span class='sc'>0 1 2</span></div>
  <div class='q'><span>每完成一个项目，系统是否会变得更聪明？</span><span class='sc'>0 1 2</span></div>
 </div>
 <div class='levels'>
  <div class='lvhead'>评分区间</div>
  <div class='lv'>0—3　探索期</div>
  <div class='lv'>4—6　场景验证期</div>
  <div class='lv'>7—8　能力形成期</div>
  <div class='lv hot'>9—10　平台化机会期</div>
 </div>
</div></div>""")

P(36, """<div class='slide center closing'>
<div class='blk'>
 <div class='l1'>别只追热门赛道，<b>要寻找结构性的供需错配</b></div>
</div>
<div class='blk'>
 <div class='l1'>别只问AI能做什么，<b>要问企业最稀缺的能力是什么</b></div>
</div>
<div class='blk'>
 <div class='final grad-text'>赛道红利给企业一个窗口<br>AI原生能力决定企业能走多远</div>
</div>
</div>""")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width":3840,"height":2160}, device_scale_factor=1)
        for n in range(1,37):
            await page.set_content(PAGES[n], wait_until="networkidle")
            await page.wait_for_timeout(120)
            out = f"/workspace/outputs/第{n}页.png"
            await page.screenshot(path=out)
            print(f"rendered {out}", flush=True)
        await browser.close()

asyncio.run(main())
