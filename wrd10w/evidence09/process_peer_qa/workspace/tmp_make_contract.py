# -*- coding: utf-8 -*-
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

doc = Document()

# 全局字体
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(12)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

for section in doc.sections:
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.17)
    section.right_margin = Cm(3.17)

def set_cn(run, font='宋体'):
    run.font.name = 'Times New Roman'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font)

def para(text, bold=False, align=None, size=None, font='宋体', space_after=6, first_indent=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    if first_indent is not None:
        p.paragraph_format.first_line_indent = Pt(first_indent)
    r = p.add_run(text)
    r.bold = bold
    if size:
        r.font.size = Pt(size)
    set_cn(r, font)
    return p

# 标题
para('兼职人员聘用合同', bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=22, font='黑体', space_after=4)
para('（媒体、广告行业适用）', align=WD_ALIGN_PARAGRAPH.CENTER, size=12, font='楷体', space_after=18)

para('甲方（聘用方）：______________________________', space_after=2)
para('法定代表人：________________ 统一社会信用代码：________________', space_after=2)
para('注册地址：____________________________________', space_after=2)
para('联系方式：________________', space_after=10)
para('乙方（受聘方）：______________________________', space_after=2)
para('身份证号码：__________________________________', space_after=2)
para('住址：________________________________________', space_after=2)
para('联系电话：________________', space_after=12)

para('根据《中华人民共和国劳动法》《中华人民共和国劳动合同法》及有关法律、法规的规定，甲乙双方本着平等自愿、协商一致的原则，就甲方聘用乙方从事兼职工作事宜，订立本合同，共同遵守履行。', first_indent=24)

# 第一条
para('第一条  合同性质与工作内容', bold=True, space_after=2)
para('1. 乙方已知悉并确认，乙方系与甲方建立非全日制（兼职）劳动关系，乙方在其他单位存在劳动关系或以其他方式就业的，不影响本合同履行；如因乙方与第三方劳动关系产生纠纷，由乙方自行承担相应责任。', first_indent=24, space_after=2)
para('2. 乙方从事的岗位为：________________（如：文案策划 / 平面设计 / 视频剪辑 / 摄影摄像 / 新媒体运营 / 广告客户执行等）。', first_indent=24, space_after=2)
para('3. 乙方的主要工作内容包括：', first_indent=24, space_after=2)
para('（1）根据甲方安排完成媒体内容策划、撰稿、编辑、审核或广告创意、设计、投放执行等工作；', first_indent=24, space_after=2)
para('（2）参与甲方承接的媒体、广告项目的制作与执行，保证工作成果符合甲方及客户的质量要求；', first_indent=24, space_after=2)
para('（3）配合甲方完成与工作相关的沟通、汇报及资料整理；', first_indent=24, space_after=2)
para('（4）双方约定的其他工作内容：________________。', first_indent=24, space_after=2)
para('4. 工作地点：________________；甲方因项目需要调整工作地点或安排远程（线上）工作的，应提前与乙方协商确认。', first_indent=24)

# 第二条
para('第二条  合同期限', bold=True, space_after=2)
para('本合同期限自 ______ 年 ____ 月 ____ 日起至 ______ 年 ____ 月 ____ 日止。合同期满，经双方协商一致可续签。', first_indent=24)

# 第三条
para('第三条  工作时间', bold=True, space_after=2)
para('1. 乙方为非全日制用工，甲方一般不安排加班；乙方每日工作时间不超过四小时，每周工作时间累计不超过二十四小时。', first_indent=24, space_after=2)
para('2. 具体工作时段由双方根据项目需要协商确定：________________________（如：每周一、三、五 14:00—18:00，或按项目排期灵活安排）。', first_indent=24, space_after=2)
para('3. 因项目进度确需延长工作时间的，双方应事先协商一致，并按本合同第四条约定支付报酬。', first_indent=24)

# 第四条
para('第四条  劳动报酬', bold=True, space_after=2)
para('1. 乙方的劳动报酬按下列第 ____ 种方式计付：', first_indent=24, space_after=2)
para('（1）小时计酬：每小时人民币 ______ 元；', first_indent=24, space_after=2)
para('（2）按件（项目）计酬：每件（项）人民币 ______ 元，计件标准与验收要求见附件或双方书面确认；', first_indent=24, space_after=2)
para('（3）按月计酬：每月人民币 ______ 元（以实际累计工作时长折算）。', first_indent=24, space_after=2)
para('2. 乙方劳动报酬不得低于甲方所在地人民政府公布的非全日制用工小时最低工资标准。', first_indent=24, space_after=2)
para('3. 甲方于每月 ____ 日前以货币形式足额支付乙方报酬；报酬结算周期最长不超过十五日。支付方式：银行转账（乙方收款账户：________________）。', first_indent=24)

# 第五条
para('第五条  保险与福利', bold=True, space_after=2)
para('1. 甲方依法为乙方缴纳工伤保险。乙方可以个人身份依法参加基本养老保险、基本医疗保险。', first_indent=24, space_after=2)
para('2. 乙方在工作期间发生工伤的，依法享受工伤保险待遇。', first_indent=24, space_after=2)
para('3. 双方另有约定的其他福利：________________。', first_indent=24)

# 第六条
para('第六条  双方权利义务', bold=True, space_after=2)
para('1. 甲方应为乙方提供必要的工作条件和安全卫生的工作环境，按时足额支付报酬，并对乙方进行必要的职业技能与安全培训。', first_indent=24, space_after=2)
para('2. 甲方安排的工作任务不得违反法律、法规，不得损害国家利益、社会公共利益及他人合法权益；广告及相关内容应符合《中华人民共和国广告法》等规定。', first_indent=24, space_after=2)
para('3. 乙方应遵守甲方依法制定的规章制度，恪守职业道德，按时保质完成工作任务，不得从事损害甲方利益或声誉的活动。', first_indent=24, space_after=2)
para('4. 乙方在兼职期间应如实告知甲方其健康状况及其他可能影响履行本合同的情形。', first_indent=24)

# 第七条
para('第七条  保密与知识产权', bold=True, space_after=2)
para('1. 乙方对在职期间知悉的甲方商业秘密（包括但不限于客户名单、报价体系、策划方案、投放数据、未公开内容等）负有保密义务，未经甲方书面同意不得向任何第三方披露或使用。保密义务不因本合同解除或终止而免除。', first_indent=24, space_after=2)
para('2. 乙方在职期间为完成甲方工作任务所创作的文案、设计、音视频、图片等作品及成果，其知识产权归甲方所有，乙方享有依法应得的署名等人身性权利（双方另有约定除外）。', first_indent=24, space_after=2)
para('3. 乙方保证其工作成果不侵犯任何第三方的著作权、商标权、肖像权等合法权益；因乙方侵权导致甲方损失的，由乙方承担相应赔偿责任。', first_indent=24)

# 第八条
para('第八条  合同的变更、解除与终止', bold=True, space_after=2)
para('1. 经双方协商一致，可以书面形式变更本合同内容。', first_indent=24, space_after=2)
para('2. 双方中任何一方均可提前三日通知对方终止本合同；甲方未按约定支付报酬或乙方严重违反甲方规章制度、严重失职给甲方造成重大损害的，对方可随时解除本合同。', first_indent=24, space_after=2)
para('3. 合同期满或双方约定的终止条件出现时，本合同即行终止。', first_indent=24, space_after=2)
para('4. 合同解除或终止时，甲方应一次性结清乙方全部劳动报酬。', first_indent=24)

# 第九条
para('第九条  违约责任', bold=True, space_after=2)
para('1. 任何一方违反本合同约定给对方造成损失的，应依法承担相应赔偿责任。', first_indent=24, space_after=2)
para('2. 乙方违反保密义务或知识产权约定的，应赔偿甲方因此遭受的直接损失。', first_indent=24)

# 第十条
para('第十条  争议解决', bold=True, space_after=2)
para('因履行本合同发生争议的，双方应协商解决；协商不成的，可依法向甲方所在地劳动争议调解组织申请调解，或依法申请劳动仲裁、提起诉讼。', first_indent=24)

# 第十一条
para('第十一条  其他', bold=True, space_after=2)
para('1. 本合同未尽事宜，按国家有关法律、法规执行；双方可另行签订书面补充协议，补充协议与本合同具有同等法律效力。', first_indent=24, space_after=2)
para('2. 本合同一式两份，甲乙双方各执一份，自双方签字（盖章）之日起生效。', first_indent=24, space_after=2)
para('3. 双方确认以下送达地址及电子邮箱用于文件送达：甲方 ________________；乙方 ________________。', first_indent=24)

para('', space_after=12)
para('甲方（盖章）：________________        乙方（签字）：________________', space_after=6)
para('法定代表人或委托代理人（签字）：____    身份证号：________________', space_after=6)
para('签订日期：______ 年 ____ 月 ____ 日      签订日期：______ 年 ____ 月 ____ 日', space_after=6)
para('签订地点：____________________________', space_after=6)

doc.save('/workspace/outputs/兼职合同.docx')
print('saved')
