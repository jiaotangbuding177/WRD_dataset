# -*- coding: utf-8 -*-
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "BVI公司设立及香港开户计划表"

thin = Side(style="thin", color="999999")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top", horizontal="left")
center = Alignment(wrap_text=True, vertical="center", horizontal="center")
title_font = Font(name="Microsoft YaHei", size=14, bold=True)
head_font = Font(name="Microsoft YaHei", size=11, bold=True, color="FFFFFF")
head_fill = PatternFill("solid", fgColor="2F5496")
sec_font = Font(name="Microsoft YaHei", size=11, bold=True, color="2F5496")
sec_fill = PatternFill("solid", fgColor="DEEBF7")
body_font = Font(name="Microsoft YaHei", size=10)
note_font = Font(name="Microsoft YaHei", size=9)

widths = {1: 6, 2: 22, 3: 62, 4: 16, 5: 34}
for c, w in widths.items():
    ws.column_dimensions[get_column_letter(c)].width = w

row = 1
ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
c = ws.cell(row=row, column=1, value="BVI设立公司 + 香港开立银行账户及证券账户 计划表（简化版）")
c.font = title_font; c.alignment = center
ws.row_dimensions[row].height = 28
row += 1
ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
c = ws.cell(row=row, column=1, value="适用背景：五个境内自然人股东以自有资金投资、直接持股设立BVI公司，并在香港开立银行账户及证券账户炒境外股票。编制日期：2026-10-23。")
c.font = note_font; c.alignment = wrap
row += 2

# ===== 第一部分：计划表 =====
ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
c = ws.cell(row=row, column=1, value="一、办理计划表（事项 / 时间 / 费用）")
c.font = sec_font; c.fill = sec_fill; c.alignment = center
row += 1
headers = ["序号", "事项", "主要内容及步骤说明", "所需时间", "相关费用"]
for i, h in enumerate(headers, 1):
    c = ws.cell(row=row, column=i, value=h)
    c.font = head_font; c.fill = head_fill; c.alignment = center; c.border = border
ws.row_dimensions[row].height = 20
row += 1

steps = [
    ["1", "前期资料准备（KYC文件）",
     "自然人股东/董事：提供护照（含签名页）；地址证明提供身份证、或近3个月信用卡对账单、或水电费单等任意一份。所有证明文件须经执业律师或注册会计师认证为真实副本后提交。",
     "约1周（视客户配合及文件核证进度）",
     "文件公证/核证费用由客户另行承担，以核证机构实际收费为准"],
    ["2", "BVI公司设立（核名及注册）",
     "流程：企业名称核准（核名费用已包含在设立费用内）→ 填写公司信息采集表、签署自然人承诺书等 → 提交经律师/注册会计师核证后的KYC证明材料 → 注册处签发公司设立证书。",
     "约2-3周",
     "设立费用 US$1,450（含核名费）"],
    ["3", "BVI公司后续年审（年度）",
     "每年缴纳公司年费，续期注册代理及注册地址，保持公司存续状态。",
     "每年一次",
     "年费 US$1,800/年"],
    ["4", "香港银行开户（面签及审核）",
     "需两位董事前往香港银行面签（股东亦可按银行要求陪同）；面签完成后由银行进行开户审核，审核通过后账户激活。代理方案三选一：南洋商业银行 / 恒生银行 / 中信银行。",
     "面签当天完成；面签后约2-3个月完成银行审核",
     "代理费：南洋 ¥25,000；恒生 ¥18,000；中信 ¥18,000。查册费（三行均为）：HK$10,000"],
    ["5", "香港证券账户开立",
     "公司银行账户开立后，凭BVI公司全套文件及董事资料向券商申请开立公司证券账户，用于买卖境外股票。",
     "约1个月",
     "一般免开户费；交易佣金、平台费等按券商届时标准收取"],
]
for s in steps:
    for i, v in enumerate(s, 1):
        c = ws.cell(row=row, column=i, value=v)
        c.font = body_font; c.alignment = wrap if i != 1 else center; c.border = border
    row += 1
row += 1

# ===== 第二部分：补充说明（同一页） =====
ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
c = ws.cell(row=row, column=1, value="二、补充说明（简化版方案）")
c.font = sec_font; c.fill = sec_fill; c.alignment = center
row += 1

notes = [
    ("1. 股权架构",
     "五个境内自然人股东以自有（境外合法）资金投资、直接持有BVI公司股权；不设立LP及GP的说法。不建议加入客户的开曼基金公司作为股东：在以自有资金投资运营炒股的情形下，加入基金公司并由其委派授权代表，容易引发监管认定风险——如被香港证监会（SFC）认定为从事受规管活动（资产管理），需持有第9号牌（资产管理受规管活动）。\n依据：《证券及期货条例》（香港法例第571章）及其附表5关于受规管活动的定义。\n提示：具体监管认定结论请由香港执业律师单独核实，本说明不构成法律意见。"),
    ("2. 董事要求备注",
     "五名自然人股东委派两名董事（为客户方具体运营人员）。董事人选可以与股东不一致，但需符合其他相应要求，包括：BVI《商业公司法》（BVI Business Companies Act, 2004）对董事的法定要求（年满18周岁、具备完全民事行为能力等），以及香港银行开户环节对董事的尽职调查（KYC）要求（如身份核验、面签配合等）。\n提示：各银行对董事及受益所有人的尽调尺度不同，最终以所选银行实际审核要求为准。"),
    ("3. 税务说明",
     "（1）香港方面：BVI公司在香港无本地雇员、无实际经营场所的离岸运作情形下，其炒卖境外股票所得一般不属于香港利得税的征税范围。香港仅对在香港经营行业、专业或业务而产生且利润源自香港的所得征收利得税（地域来源征税原则）。需注意：如公司在香港租用办公室、聘用员工或以其他方式构成在港实际经营，相关利润可能需缴纳利得税（两级制税率8.25%/16.5%）。\n依据：《税务条例》（香港法例第112章）第14条及地域来源征税原则；税务上诉案例确立的运作测试（operations test）。\n（2）境内方面：境内自然人股东作为中国税务居民，就其境外所得仍负有纳税义务——自BVI公司取得的股息红利、转让股权或公司注销分配取得的所得，需按20%税率缴纳个人所得税。\n依据：《中华人民共和国个人所得税法》第三条（利息、股息、红利所得及财产转让所得适用20%比例税率）及其实施条例关于境外所得的规定。\n提示：CRS金融账户信息交换下，境外账户及持股信息可能被交换至境内税务机关，建议就具体申报及税务安排单独咨询税务师核实。"),
    ("4. 费用折算估算（简化版方案）",
     "按2026-10-23参考汇率折算（US$1 ≈ ¥6.68，HK$1 ≈ ¥0.85，汇率每日波动，以实际结汇汇率为准）：\n• BVI设立费用 US$1,450 ≈ ¥9,686\n• BVI后续年费 US$1,800/年 ≈ ¥12,024/年\n• 香港开户代理费（恒生或中信方案）¥18,000；（南洋方案）¥25,000\n• 银行查册费 HK$10,000 ≈ ¥8,500\n综合估算（首期支出，含查册费，不含BVI年费、文件公证费及证券交易费用）：\n• 恒生/中信方案：US$1,450 + ¥18,000 + HK$10,000 ≈ ¥36,186\n• 南洋方案：US$1,450 + ¥25,000 + HK$10,000 ≈ ¥43,186\n如需同时预留首笔年费US$1,800（≈¥12,024），上述两项分别约 ¥48,210 / ¥55,210。"),
]

for title, body in notes:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    c = ws.cell(row=row, column=1, value=title)
    c.font = Font(name="Microsoft YaHei", size=10, bold=True)
    c.alignment = wrap; c.border = border
    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    c = ws.cell(row=row, column=1, value=body)
    c.font = body_font; c.alignment = wrap; c.border = border
    nlines = body.count("\n") + 1
    ws.row_dimensions[row].height = max(30, nlines * 15 + 20)
    row += 1
row += 1
ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
c = ws.cell(row=row, column=1, value="免责声明：本计划表依据客户提供的资料及公开法律框架整理，仅供内部参考；涉及的各项法律、税务及监管结论（含9号牌认定、香港利得税及境内20%个税事项）均请由执业律师、注册会计师或税务师单独核实后采用。")
c.font = note_font; c.alignment = wrap

ws.freeze_panes = "A4"
ws.sheet_view.showGridLines = False
out = "/workspace/outputs/BVI公司设立及香港银行证券账户计划表.xlsx"
wb.save(out)
print("saved:", out)
