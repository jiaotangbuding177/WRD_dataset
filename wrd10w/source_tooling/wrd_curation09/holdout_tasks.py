"""Build actual held-out task inputs and evaluator-only rubrics, never answers.

The task source selection and rubric are new offline annotations. No model,
saved resource script, agent loop, or business task is run by this builder.
"""
import collections,gzip,hashlib,json,re,shutil
from pathlib import Path
ROOT=Path('D:/skillloop');OUT=ROOT/'output/20261031_wrd_curation09/holdout';CLEAN=ROOT/'output/20261027_wrd_main_v10/clean_inputs'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
 with gzip.open(p,'rt',encoding='utf-8-sig') as f:return [json.loads(s) for s in f]
def digest(x):return hashlib.sha256(x if isinstance(x,bytes) else x.encode()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'path':str(p.relative_to(OUT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
pool={r['source_id']:r for r in rows(CLEAN/'source_pool.with_body.jsonl.gz')}
res=read(OUT/'holdout_reservation.json');recovery=read(OUT/'MATERIAL_RECOVERY_AND_ANCESTRY.json')
groups={s:g for g in res['groups'] for s in g['source_ids']}
configs=[]
def add(sid,title,indices,kind,checks,**kw):
 configs.append({'source_id':sid,'title':title,'indices':indices,'output_kind':kind,'checks':checks,**kw})

# Actual requests and their complete necessary antecedents. Indices refer to
# preserved user-occurrence order, not authenticated native tool chronology.
add('conv_007d40b3886f','高校基金形式审查可勾选Word清单',[0,1],'docx',[
 '形成可下载且可打开的Word清单；具有可勾选选项和客户确认位置。',
 '覆盖申请资格、材料与签章、限项/重复、预算与伦理等适用性检查；不同项目规则明确待客户核实。',
 '不得捏造某一基金当年具体指南、截止日期或本单位政策。'],mechanism='checklist_document')
add('conv_0400aac342b0','教育平台入选表述润色',[0],'text',[
 '优化原句后半句，保留“入选由教育部指导建设的平台AI试验场”事实强度。',
 '不升级为教育部认证、官方指定、全国唯一、获奖或应用成效。',
 '提供可直接使用的简洁中文表述。'],mechanism='source_faithful_rewrite')
add('conv_08457c6c88dc','凤凰文创盲盒设计图',[0],'image',[
 '金色凤凰、半开朱红方盒、宣纸背景及飞鸟集题字/印章等主要构图对应需求。',
 '艺术纹样按左右翼和尾端的朝代段落区分，不把全部要求仅复述成文字。',
 '真实图片文件可打开；风格完整且文字/细节问题如实记录。'],mechanism='prompt_to_image',
 adaptation='同组件另一来源为高清品质近重复。本任务采用本源逐字版本，末尾“low品质”保留为原歧义，不默改为高清；相关质量维度需dev校准。')
add('conv_12ac99dd2fa7','FDE社区命名',[0,1,2,3,4,5],'text',[
 '围绕AI连接百行百业、企业需求与青年FDE工程师社区提出名字。',
 '响应用户希望大胆、有辨识度的偏好；不重复仅保守地域式命名。',
 '不保证商标/域名可注册或虚构市场调研结果。'],mechanism='iterative_naming')
add('conv_15f0f4d89d3f','数字素养月介绍审校',[2],'text',[
 '保留背景、实施、活动成效与示范价值的合理结构。',
 '保留用户提供的33位领军教师、近1000名教师及四位一体模式，不杜撰成效。',
 '把全国首款、填补空白、国家平台隶属等过强归因作为待核或作忠实限定。'],mechanism='source_faithful_review')
add('conv_24de551a33dd','面向领导的AI寄语',[0,1,2],'text',[
 '输出适合领导场合的一句话寄语，表达主动拥抱AI、能力提升的意图。',
 '措辞含蓄得体，不再用淘汰不会使用者的直白威胁式表述。',
 '不擅加政策背书、事实或承诺。'],mechanism='audience_rewrite')
add('conv_24e59c8da83e','正式柔和的联系请求改写',[0,1],'text',[
 '保留发件人角色、会议/项目LP关系及索取Simon联系方式的目的。',
 '正式、柔和、简洁，不将请求改成命令或新增承诺。',
 '输出为文案，不冒称已发邮件或已取得联系人信息。'],mechanism='email_draft',side_effects='offline_draft_only_no_send')
add('conv_2dff0a98f3d5','创业团队产品运营JD',[0,1,2,3,4,5],'text',[
 '生成可招聘使用的JD，覆盖AI工具、用户问题收集、文档案例/视频协作及共同定优先级。',
 '保留优秀应届生可考虑，不擅自添加高年资/学历硬门槛。',
 '不公开原内部技术架构+5研发+1运营的精确人数配置。'],mechanism='corrected_requirement_JD')
add('conv_2e1d20b1fc34','创始人后端候选人面试设计',[0],'text',[
 '给出可用于面试的提问及观察要点，覆盖AI辅助编码、长期成长和团队协作。',
 '评价方式能区分具体证据与自述，不仅列宽泛品质名词。',
 '无候选简历时不捏造背景或给出录用结论。'],mechanism='interview_plan')
add('conv_30474e7027ac','产教融合会议封面图',[0],'image',[
 '16:9构图、上海天际线与AI光线、蓝白少量金色，整体庄重。',
 '主标题/副标题/会议小字与原要求对应，可读性单独评价。',
 '输出真实图片文件，不以提示词冒充成品。'],mechanism='specified_text_image')
add('conv_3a27f499e502','3D打印介绍文档',[0],'document',[
 '生成可打开的介绍文档，说明基本原理、常见工艺、材料与应用。',
 '区分不同工艺适用性，不把所有3D打印都写成同一流程。',
 '不杜撰特定公司的性能、价格或用户未给出的案例数据。'],mechanism='technical_intro_document')
add('conv_589813f393e6','贪吃蛇HTML游戏',[0],'html',[
 '交付可离线打开的HTML游戏；jtml按上下文作为可能笔误，若直接按HTML处理须说明。',
 '实际游戏可开始、控制移动、吃食物增长、碰撞结束并可重开，另由运行评测验证。',
 '不能仅有静态页面或声称测试通过而无执行证据。'],mechanism='interactive_HTML')
add('conv_9bc7947f7ce1','小猪快跑HTML游戏',[0],'html',[
 '交付可打开的HTML，呈现小猪奔跑的可操作玩法。',
 '开始/控制、障碍或挑战、结束/重开形成闭环；具体玩法可合理设计。',
 '不把外链截图或静态装饰当可玩游戏。'],mechanism='interactive_HTML')
add('conv_b0766d5cdf61','房屋设计网页及图片导出',[0,1,2],'html',[
 '交付房屋设计网页；烟囱应位于房顶，提供导出图片功能。',
 '新建完整状态时实现必要的房屋展示与可操作设计，不依赖不存在的旧代码。',
 '导出的图片确实包含当前设计，离线打开和交互须后续真实运行。'],mechanism='interactive_HTML_export',
 adaptation='把原初始要求和后续明确纠正作为新建功能状态的已知需求，未导入缺失旧网页；不是原黑屏/位置错误的原生修复重放。')
add('conv_dd0ca1b95895','下载位置困惑的产品改进建议',[0],'text',[
 '区分文件已下载但用户找不到和下载失败两类问题。',
 '给出符合浏览器权限边界的反馈、引导和可发现性改进。',
 '不声称网页能无条件读取/控制用户本地下载目录。'],mechanism='product_feedback_diagnosis')
add('conv_ca2369adba0b','学习委员典型事例润色',[2],'text',[
 '保留作业统计、责任耐心、学科综合评价A、800米优秀这些原事实。',
 '优化表达、突出事例，不虚增荣誉、名次、次数或工作影响。',
 '不把失败续接提示当事例正文。'],mechanism='factual_personal_rewrite')
add('conv_874f133d1919','QQ浏览器下载窗口故障排查',[0],'text',[
 '将可能原因作为假设，给出由低风险到深入的可执行排查步骤。',
 '缺系统/版本/复现条件时明确需要的信息。',
 '不能假称已访问用户电脑、查到根因或直接建议大范围删除数据。'],mechanism='diagnostic_plan')
add('conv_143452559f75','Gitee工作项缺项澄清',[0,1,2,3,4],'clarification',[
 '区分6类问题并保持缺陷/任务/需求分类与默认张文指派偏好。',
 '仓库不明确时先在可用授权工具内定位；本包不提供真实Gitee环境，不得杜撰已创建。',
 '无可访问仓库时请求项目地址/最少定位信息，已知问题不丢失。'],mechanism='controlled_clarification',
 task_class='clarification_only',adaptation='本包仅评估信息不足分支，未提供Gitee副作用环境；不计实际建单TSR。')
add('conv_2670b00882a9','无长期记忆的个人画像边界',[0],'clarification',[
 '只整理当前确可访问的信息，不编造姓名、年龄、职业或项目。',
 '尊重五类标题、日期未知写unknown及代码块格式。',
 '如长期记忆未提供，明确限制并请用户补充，而非假称已全量读取。'],mechanism='controlled_clarification',
 task_class='clarification_only',adaptation='原长期记忆环境不可恢复。本包明确无长期记忆挂载，只评价有界整理/澄清，不计完整画像业务成功。')

# Real attachment tasks. Attachments selected by their exact restored SHA.
add('conv_0471e84eb55a','工程化益生菌研发候选评估',[1],'text',[
 '逐一覆盖六个实际PDF候选；以岗位必须项、学历和工程菌/基因编辑证据判断。',
 '每个关键经历/学历判断能追溯到文件/页；无法确定的能力为待验证。',
 '不得把普通菌培养、动物实验或泛科研背景直接当已证工程化能力；不使用未附候选人的比较结论。'],
 mechanism='multi_PDF_candidate_matching',materials='ALL',
 adaptation='新作者将同源恢复的六份真实PDF固定为本次候选池，使用原JD原文；不重放缺失史海霞/候春利记录的历史比较表。')
add('conv_050cdce318d9','硬件产品经理评估Word',[0,4,5],'docx',[
 '交付何晓明候选人的可打开Word评估报告，和提供的硬件产品经理JD逐项匹配。',
 '说明可推荐/有条件/不推荐的证据和差距，不以多年经验自动替代硬件产品定义能力。',
 '不混入另一候选人肖豪的信息，不杜撰未给经历或薪资承诺。'],mechanism='PDF_to_JD_report',
 material_SHA=['380d0800afb1f00172b0291ccc37b364ad06bf3b6df63f046d029b5aa60e18c0'])
add('conv_06d3b452f1d2','五份后端候选简历推荐',[1,3],'text',[
 '覆盖附带五个候选PDF并给出可进入面试的建议。',
 '区分后端基础、项目证据、LLM/Agent加分与成长性未知。',
 '不用职位标签代替项目事实，不混淆候选人的公司/年限/技术栈。'],mechanism='multi_PDF_candidate_matching',materials='ALL')
add('conv_db09358aab86','十份后端简历与JD匹配',[0,1],'text',[
 '逐个覆盖10份实际PDF候选，结论和原JD要求关联。',
 '不把简历未列某技术写成确定不会；区分已证/待核和面试追问。',
 '不得从后来无关硬件岗位/办公地址问题引入错误JD。'],mechanism='multi_PDF_candidate_matching',materials='ALL',
 extract_question_indices=[1])
add('conv_fb33437938a8','前端快应用候选评估',[1],'text',[
 '覆盖6份PDF，围绕小程序/快应用/H5、框架、WebSocket、工程化与成长性评价。',
 '推荐理由和风险来自各自简历，能定位原文件/页。',
 '不将PromptGuard、检索噪声或未附履历当真实候选事实。'],mechanism='multi_PDF_candidate_matching',materials='ALL')
add('conv_cde87bf0074c','医疗器械采购候选匹配',[0,1],'text',[
 '基于陆飞真实简历与原采购JD给匹配建议。',
 '注意PDF所列大专与JD本科条件的差异，以及医疗器械研发生产型企业经验是否确证。',
 '不把诊所/养老采购经历无条件等同三类有源设备研发生产经验；结论保留待核边界。'],
 mechanism='PDF_to_JD_report',materials='ALL',extract_question_indices=[1])
add('conv_495ce24cf535','生产运营总监两份评估报告',[0,3],'text',[
 '分别覆盖宋先生和黄和芳两份真实PDF，与当前可见岗位说明摘录相联系。',
 '区分大公司优化经验与从混乱中建体系、多场地/定制研发型生产能力。',
 '原岗位DOCX未恢复，不补造原文件缺段或声称全文已审。'],mechanism='multi_PDF_candidate_matching',materials='ALL',
 adaptation='显式改造为基于原会话可见JD摘录的有限评估。没有把摘录伪造成原岗位DOCX，结论只能覆盖已给条件。',
 preface='当前可用的岗位材料是下列原会话摘录，完整岗位DOCX未提供；请明确哪些条件尚无法核实。')
add('conv_2680d1b5f71e','依据图片精简求职者公司介绍',[1,2],'text',[
 '只使用两张实际图片可见业务：智慧安全巡检/作业机器人、复合机器视觉及相关工业场景。',
 '输出两种不同方向的精简求职者介绍，表达清楚。',
 '不从源会话前一地址查询杜撰广州/江西/山东具体地址，也不把宣传性领先表述升级为独立核验结论。'],mechanism='image_grounded_summary',materials='ALL')
add('conv_39ee73dad7d3','MJ6销售管理制度完善',[2],'docx',[
 '基于实际DOCX完善销售佣金/提成管理，保留原适用范围、备案、贡献比例、审批和利益冲突框架。',
 '新增条款与建议明确区分，不擅自改变既有佣金比例、结算条件或虚构法规确定性。',
 '生成可打开Word，内容完整且序号/交叉引用可检查。'],mechanism='source_policy_revision',
 material_SHA=['6ab4fb12d5dcc6f38954fc87b19efc9f4fb1ce650df92b04ef2ee0b308562953'],extract_question_indices=[2])
add('conv_ed0d158f38e3','知识产权协议年费条款全文提取',[0],'text',[
 '全文检查18物理页，提取3.5未缴年费失效相关责任、7.1标的成果维持费、7.2关联成果维持费条款。',
 '条款位置/原文摘录/义务方/触发条件分列；7.2的另有协议和登记备案条件保留。',
 '文本未明示的具体缴费日、金额、通知机制不得补造；不将乙方或丙方协商承担偷换为学校当然承担。'],
 mechanism='whole_PDF_clause_extraction',materials='ALL')
add('conv_3a4f18d72252','病理研究DOCX转逐页PPT图片',[3],'slide_images',[
 '根据真实DOCX制作有序逐页PPT图片，信息层级清楚且可读。',
 '保留源内容、数值和假设/预测身份，不把源报告的未经核实商业主张升级为事实。',
 '不谎称已安装或调用未固定的外部Humanize技能。'],mechanism='document_to_slides',materials='ALL',
 adaptation='选取最后独立的逐页图片请求；未提供Humanize技能仓库，执行方法不固定为该外部技能，不冒充原技能安装条件重放。')
add('conv_fa46a4502e37','两主体PPT材料的目标澄清',[0,1,2],'clarification',[
 '识别真实PDF和PPTX介绍不同主体，当前没有明确目标主体或两者关系。',
 '提出最少的目标/材料关系澄清问题，不擅自合并企业、产品、营收或客户。',
 '不假称已完成公司PPT；本澄清分支不计公司PPT交付TSR。'],mechanism='PDF_PPT_enrichment',materials='ALL',
 task_class='clarification_only',adaptation='上海威蓝汽车PDF与安徽海姬尔护理机器人PPTX属于两个不同主体，原题未给关系或目标主体。本包只评估澄清，不计公司PPT交付TSR。')
add('conv_feb7c0fed490','活动参会可行性分析',[2],'text',[
 '根据实际邀请函提取活动时间、地点、议程和对象；与用户说明的企业定位/目标分开。',
 '收益、成本与风险按可知范围分析；没有预算和参与费时不伪造投入产出金额或确定收益。',
 '给分级/条件化建议与待核事项，不预设应参加。'],mechanism='event_document_decision',
 material_SHA=['66b54d4cfe9c36527d950a32bfbae875bd45c44324dda087c6ac591b03e55942'],
 preface='请以2026-10-12为决策时点，将所附邀请函作为该情景给定输入，作活动发生前的分析，不引用该日以后的实际活动结果。',
 adaptation='原请求时间为2026-08-26T23:58:40.518Z，无法证明那时已收到当前导出附件版本。本情景改用原导出已封存的2026-10-12作为固定决策时点，明确不是原native条件重放。')
add('conv_f075f2e6dfea','给定语音输入方案与EvoMind关联分析',[12,13],'docx',[
 '基于实际提供的语音输入方案和用户所问分析关联，形成可打开Word。',
 '明确给定文档是2026年6月材料，价格/功能为源中主张而非当前已核实事实；缺实际EvoMind架构时列条件。',
 '不假称已集成SDK、注册服务、获取凭据或验证实时价格。'],mechanism='source_plan_analysis',materials='ALL',
 extract_question_indices=[12],adaptation='只挂同组真实MD及原后续问题，不导入前期外部竞品搜索、简历或体检等无关内容。')

# Three authentic reservations that cannot become independent component cases.
add('conv_420fd0fd1158','科委DOCX转正式PDF',[1],'pdf',[
 '实际DOCX存在，但私有背景文本已进入current569；不是独立新dev题。'],
 mechanism='document_conversion',materials='ALL',hold='CONTENT_ANCESTOR_ALREADY_VISIBLE_IN_CURRENT_TRAIN')
add('conv_ea9b88b23b98','前端招聘流程Word总结',[2,3],'docx',[
 '真实MD存在，但招聘流程表格已在current569历史assistant输入暴露。'],
 mechanism='document_summary',materials='ALL',hold='CONTENT_ANCESTOR_ALREADY_VISIBLE_IN_CURRENT_TRAIN')
add('conv_23a12ab71383','记忆安全博士研究设计',[62],'text',[
 '原请求要根据文章设计三个前沿研究点；只恢复笔记和方案，未恢复/核实完整原论文。',
 '同包已有博士方案型文档，不能把答案样材料当未见能力证据。'],
 mechanism='research_design',materials='ALL',extract_question_indices=[62],
 hold='PRIMARY_PAPERS_NOT_RECOVERED_AND_ANSWERLIKE_SOURCE_NOT_INDEPENDENT_RESEARCH_GOLD')

# Later content-level review: these CV bytes are unseen, but their private JD
# is already visible in current training. Preserve the tasks as near-domain
# candidates; do not advertise whole-source-independent test qualification.
for config in configs:
 if config['source_id'] in {'conv_050cdce318d9','conv_06d3b452f1d2','conv_db09358aab86'}:
  config['hold']='PRIVATE_JD_ALREADY_VISIBLE_IN_CURRENT_TRAIN_NEAR_DOMAIN_ONLY'
 if config['source_id'] in {'conv_fb33437938a8','conv_cde87bf0074c','conv_0471e84eb55a','conv_143452559f75'}:
  config['hold']='EXACT_PRIVATE_REQUEST_ALIAS_IN_ORIGINAL226_H12_OR_STATIC_USER_INPUT'

assert len(configs)==36 and len({groups[c['source_id']]['source_scope_component_id'] for c in configs})==36
common_dimensions=[
 {'id':'source_fidelity','name':'事实与来源忠实','weight':20,'anchors':{'0':'出现关键捏造/错归属','2':'基本正确但关键证据或限定缺失','4':'关键事实、引文和未知项均忠实可核'}},
 {'id':'requirement_coverage','name':'需求覆盖','weight':20,'anchors':{'0':'未回应核心委托','2':'覆盖部分要求','4':'核心要求和明确纠正均覆盖'}},
 {'id':'functional_usability','name':'交付可用性','weight':20,'anchors':{'0':'没有真实交付或不可用','2':'有限可用/主要功能待证','4':'目标格式/功能在实际运行或人工核验中可用'}},
 {'id':'organization_presentation','name':'组织与表达','weight':20,'anchors':{'0':'难以理解或严重版式问题','2':'基本清楚有明显冗余/层次问题','4':'清晰、有序、适配受众与格式'}},
 {'id':'evidence_boundaries','name':'证据边界与判断','weight':20,'anchors':{'0':'无证成功/权限/法律或业务确定性','2':'部分区分事实和建议','4':'推断、条件、未知和实际执行状态区分清楚'}}]
task_rows=[];hold_rows=[];catalog=[]
for config in configs:
 sid=config['source_id'];g=groups[sid];source=pool[sid];users=source['user_messages']
 task_id='wrd09_'+g['split']+'_'+g['source_scope_component_id'].removeprefix('v10_group_')
 td=OUT/'tasks'/task_id;td.mkdir(parents=True,exist_ok=True)
 selected=[];original_links=[]
 for i in config['indices']:
  msg=users[i];text=msg['content']
  if i in config.get('extract_question_indices',[]):
   assert '用户原始问题:' in text
   text=text.rsplit('用户原始问题:',1)[1].split('[附加文件:',1)[0].strip()
  selected.append(text)
  original_links.append({'source_id':sid,'user_occurrence_index':i,'message_id':msg['id'],
   'full_original_content_sha256':digest(msg['content']), 'selected_text_sha256':digest(text),
   'extraction':'literal question after original 用户原始问题 marker' if i in config.get('extract_question_indices',[]) else 'verbatim full original user occurrence'})
 material_specs=source['authentic_materials'] if config.get('materials')=='ALL' else [m for m in source['authentic_materials'] if m['sha256'] in config.get('material_SHA',[])]
 aliases=[]
 for j,m in enumerate(material_specs,1):
  name=Path(m['native_path']).name;filename=f'{j:02d}_'+re.sub(r'^[0-9]+_','',name)
  p=td/'inputs'/filename;p.parent.mkdir(parents=True,exist_ok=True)
  original=OUT/'objects'/m['sha256'][:2]/m['sha256'];shutil.copyfile(original,p)
  assert digest(p.read_bytes())==m['sha256']
  aliases.append({'native_path':'/workspace/inputs/'+filename,'relative_path':'inputs/'+filename,
   'sha256':m['sha256'],'bytes':m['bytes'],'original_native_alias':m['native_path'],'historical_bytes_unmodified':True})
 body=(config.get('preface','')+'\n\n' if config.get('preface') else '')+'\n\n'.join(selected)
 # A new functional-state request must not imply a missing old file is present.
 if config.get('adaptation') and sid=='conv_b0766d5cdf61':
  body+='\n\n本次从头创建网页，当前没有旧网页文件。上述烟囱位置和图片导出要求均为本次已知需求。'
 if sid=='conv_0471e84eb55a':body+='\n\n本次候选池为下列六份实际附带PDF，请逐一匹配。'
 if sid=='conv_2670b00882a9':body+='\n\n本次环境没有提供长期记忆或个人知识库，只能使用这条请求中明确出现的信息。'
 if sid=='conv_143452559f75':body+='\n\n本次未提供可访问的Gitee项目环境或项目地址；请在真实信息与权限范围内处理，不假称已建单。'
 if sid=='conv_fa46a4502e37':body+='\n\n现有两份文件分别介绍不同企业/项目，未提供两者关系和本次目标主体；请先明确需要哪些最少信息再推进，不擅自把两个主体合并。'
 if aliases:body+='\n\n本次实际附加文件（请以这些路径为准）：\n'+'\n'.join(a['native_path'] for a in aliases)
 status='HOLD' if config.get('hold') else 'INPUT_READY_COMPONENT_NOT_EXECUTED'
 task_class=config.get('task_class','component_delivery')
 packet={'schema':'wrd09-native-evaluation-input-v1','task_id':task_id,
  'messages':[{'role':'user','content':body}],
  'input_files':aliases,'expected_output_kind':config['output_kind']}
 save(td/'input05.json',packet)
 (td/'prompt05.txt').write_text(body+'\n',encoding='utf-8')
 rubric={'schema':'wrd09-evaluator-rubric-v1','task_id':task_id,'annotation_author':'/root/scheduled_batch24 (new offline annotation)',
  'evaluation_level':'COMPONENT_OR_CONSUMPTION',
  'not_original_teacher_reasoning_or_tool_feedback':True,'source_basis':original_links,
  'task_specific_criteria':config['checks'],'quality_dimensions':common_dimensions,
  'quality_formula':'Q=sum(weight*dimension_score/4), each dimension 0..4; report all five separately and missing dimensions UNKNOWN; not multiplied by TSR.',
  'threshold_status':'UNCALIBRATED_NEW_RUBRIC_DEV_ONLY_CALIBRATION_REQUIRED',
  'qualified_skill_threshold':None,'student_quality_observed':None,'TSR_observed':None,
  'business_completion_denominator_eligible':task_class=='component_delivery' and not config.get('hold'),
  'clarification_scoring_separate_from_business_TSR':task_class=='clarification_only',
  'no_exact_reference_answer_or_ranking_fabricated':True,
  'checks_that_require_future_execution':config['output_kind'] in ['html','image','slide_images','docx','pptx','pdf','document'],
  'full_autonomous_WRD_or_KEEP_evidence_created':False,
  'cost_fields_to_record':['request/response usage including unknown','all tool execution elapsed time','retries/failures','model and runtime identity','energy if metered','cash if known','human/AI curation cost not zero'],
  'historical226_H12_static_results_used_to_choose_thresholds':False,
  'review_protocol':'Freeze before any student output. Development may calibrate a later version; keep original rubric immutable. Blind test outputs must not drive training/threshold changes.'}
 save(td/'rubric.evaluator_only05.json',rubric)
 record={'task_id':task_id,'title':config['title'],'split':g['split'],'source_scope_component_id':g['source_scope_component_id'],
  'reserved_source_ids':g['source_ids'],'selected_source_id':sid,'status':status,'task_class':task_class,
  'hold_reason':config.get('hold'),'output_kind':config['output_kind'],'mechanism':config['mechanism'],
  'authorship':'NEW_OFFLINE_TASK_SELECTION_AND_RUBRIC; original selected requirements/material bytes pinned separately',
  'evaluation_level':'COMPONENT_OR_CONSUMPTION',
  'adaptation':config.get('adaptation'),'original_native_input_equivalence_claimed':False,
  'source_requirement_pins':original_links,'task_input_pin':pin(td/'input05.json'),
  'rubric_pin':pin(td/'rubric.evaluator_only05.json'),'material_aliases':aliases,
  'historical_assistant_answer_in_input':False,'resource_graph_isolation_known_only':True,
  'requires_future_native_runtime_preflight':True,'eligible_for_training':False,
  'model_or_actor_executed':False,'full_autonomous_WRD_validation_task':False,
  'independent_skill_consumer_pair_available':False}
 catalog.append(record)
 if config.get('hold'):hold_rows.append(record)
 else:task_rows.append(record)
save(OUT/'TASK_CATALOG_ALL36_05.json',catalog)
for split in ['dev','test']:
 path=OUT/f'{split}.tasks05.jsonl'
 with path.open('w',encoding='utf-8',newline='\n') as f:
  for r in task_rows:
   if r['split']==split:f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
save(OUT/'HELD_TASKS05.json',hold_rows)
summary={'schema':'wrd09-holdout-task-build-summary-v1','status':'ACTUAL_COMPONENT_TASK_INPUTS_AND_RUBRICS_CREATED_NOT_RUN',
 'reservation_groups':36,'reservation_sources':40,'input_ready_groups':len(task_rows),'held_groups':len(hold_rows),
 'by_split_status':{split:dict(collections.Counter(r['status'] for r in catalog if r['split']==split)) for split in ['dev','test']},
 'by_split_task_class':{split:dict(collections.Counter(r['task_class'] for r in task_rows if r['split']==split)) for split in ['dev','test']},
 'full_business_component_delivery_tasks':sum(r['task_class']=='component_delivery' for r in task_rows),
 'explicit_clarification_only_tasks':sum(r['task_class']=='clarification_only' for r in task_rows),
 'explicit_adapted_input_states':sum(bool(r['adaptation']) for r in task_rows),
 'original226_H12_static_result_informed_gold':False,'full_autonomous_WRD_evaluation_cases':0,
 'qualified_KEEP_or_student_rollouts_created':0,'student_dev_test_token_arrays_created':0,
 'input_materials_restored':49,'original_material_reference_entries':51,
 'known_resource_ancestry_before_content_audit':str(OUT/'MATERIAL_RECOVERY_AND_ANCESTRY.json'),
 'private_content_conflicts':str(OUT/'PRIVATE_CONTENT_ALIAS_HOLD.json'),
 'primary_papers_missing_research_task_held':True,'test_outputs_observed':0,
 'evaluation_level':'COMPONENT_OR_CONSUMPTION',
 'private_JD_seen_in_training_held_groups':3,
 'private_request_seen_in_protected_user_inputs_held_groups':4,
 'new_training_targets':0,'training_started':False,'new_business_Teacher_Actor_calls':0,'AI_curation_cost':'UNKNOWN_NOT_ZERO',
 'script_sha256':digest(Path(__file__).read_bytes()),
 'evaluation_limit':'These are actual independent-component task inputs, not demonstrated end-to-end WRD trials. Full autonomous skill evaluation still needs a native parent task and distinct consumer task/materials for each retained version.'}
save(OUT/'TASK_BUILD_SUMMARY05.json',summary)
print(json.dumps(summary,ensure_ascii=False))
