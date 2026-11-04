"""Create explicit new-author correction proposals, never run writer programs.

Four full original programs remain immutable. Each proposal may become ONE
whole-program edit example only after the parent's actual resource validation.
"""
from pathlib import Path
import ast,hashlib,json

BASE=Path(__file__).resolve().parent
def H(b):return hashlib.sha256(b).hexdigest()
def P(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':H(b)}

def main():
 qa=json.loads((BASE/'THREE_PROGRAM_SEMANTIC_QA02.json').read_text(encoding='utf8'))
 replacements=[
  ('主导解决产品开发过程中的技术难题','主导解决产品开发过程中的技术难题','解决产品开发过程中的技术难题'),
  ('编写并维护各类技术文档','编写并维护各类技术文档','编写技术文档'),
  ('健康咨询Agent服务超5万用户零投诉','健康咨询Agent服务超5万用户零投诉','健康咨询Agent据录音总结称服务超5万用户、未发生医疗安全投诉'),
  ('薪资预期显著高于其他候选人','薪资预期显著高于其他候选人（原package约19K+14K年终），创业公司6人团队预算能否覆盖需先内部确认。','据录音总结，原薪资为19K base加14K年终奖，期望薪资可按岗位职责与面试情况合理确定；实际薪资预期与公司预算能否匹配仍需沟通确认。'),
  ('已按用户决定安排终面','已按用户决定安排终面','用户已选择面试，是否进入终面待确认'),
  ('用户已确认仅面左，本报告附其面试提纲','建议：推荐进入下一轮（用户已确认仅面左，本报告附其面试提纲）。','建议：按用户仅面左的选择准备面试提纲；是否进入终面仍待确认。'),
  ('终面原约张江双子塔A塔现场','终面原约张江双子塔A塔现场，按用户要求调整为线上执行','按本次委托采用线上形式；原录音总结有张江双子塔A塔现场终面提议，源材料也有尚未明确进入终面的说明，具体轮次与预约未核实'),
  ('除为备份数据所必需的下载、复制外','除为备份数据所必需的下载、复制外','除下载数据备份外'),
  ('包括数据丢失、业务中断或生产损失等','包括数据丢失、业务中断或生产损失等','包括人身伤害或生产损失'),
  ('将优先依据企业已有的制度与流程文件','智能体在回答和生成建议时，将优先依据企业已有的制度与流程文件，避免输出缺乏制度或流程依据的业务信息。','智能体回答和生成建议时应优先引用已编译的证据原子，避免编造未被制度或流程文件支持的业务事实。'),
  ('以下仅保留原始文本中与「我的分享」相关的现存内容',"doc.add_heading('6. 工作区文件管理', level=1)\np('（本节内容未包含在本次评审所依据的原始文本中，修订版不作补写。以下仅保留原始文本中与「我的分享」相关的现存内容。）', italic=True)\np('在「我的分享」面板查看所有分享；支持取消分享、修改权限。')", "doc.add_heading('6. 工作区文件管理（原文缺失）', level=1)\np('（本节内容未包含在本次评审所依据的原始文本中，修订版不作补写。）', italic=True)\ndoc.add_heading('待定位原文片段：我的分享', level=1)\np('以下摘录来自所提供的原文片段，其原节号归属未核实，不据此补写第6节。', italic=True)\np('在「我的分享」面板查看所有分享；支持取消分享、修改权限。')"),
  ('支持多种调度类型，可按需设置周期选项','支持多种调度类型，可按需设置周期选项。','支持三种调度类型；具体类型名称及周期选项未在所提供文本中列明，需以补充材料核实。'),
  ('未虚构任何内容','无法核实的数字与缺失列表均采用概述性表述，未虚构任何内容。','所提供的数字按原文保留；缺失列表和缺失节号不推测补写，另行标明待核实事项。'),
 ]
 replace_by_key={x[0]:x for x in replacements};assert len(replace_by_key)==13
 entries=[];dest=BASE/'proposed_corrected_programs';dest.mkdir(exist_ok=True)
 for f in qa['findings']:
  p=Path(f['original_code']['path']);original=p.read_bytes().decode('utf8');assert H(original.encode())==f['original_code']['sha256'];revised=original;changes=[]
  for finding in f['mandatory_zero_loss_code_ranges']:
   key=finding['literal_problem_excerpt'];_,old,new=replace_by_key[key];assert revised.count(old)==1,(key,revised.count(old));original_start=original.index(old);revised=revised.replace(old,new,1)
   changes.append({'original_finding':finding,'oldText':old,'newText':new,'original_oldText_range':{'start':original_start,'end':original_start+len(old),'coordinate':'Original full write.arguments.content Unicode codepoints, half-open'},'oldText_SHA256':H(old.encode()),'newText_SHA256':H(new.encode()),'provenance':'NEW_AUTHORED_LITERAL_SOURCE_RESTORATION_OR_EXPLICIT_UNCERTAINTY_NOT_ORIGINAL_REPAIR_TRACE','confidence':'DIRECT_LITERAL_GROUNDING_FOR_FIXED_FACT_OR_EXPLICIT_UNKNOWN_FOR_UNVERIFIED_APPOINTMENT_SECTION_PLACEMENT','business_or_legal_truth_beyond_source_claimed':False})
  ast.parse(revised);q=dest/(f['target_owner_id']+'.proposed.py');q.write_bytes(revised.encode())
  entries.append({'original_owner_id':f['target_owner_id'],'source_ids':f['source_ids'],'original_program':P(p),'proposed_program':P(q),'whole_program_edit_example_budget':1,'original_program_preserved':True,'change_count':len(changes),'changes':changes,'actual_old_Agent_tool_edit':False,'actual_new_program_run':False,'must_validate_before_training':['Root verifies all oldText and newText against source observations and original constraints.','Run complete program in fixed97a0 disposable resources environment; no model/Agent calls.','Compare generated docx XML/text with original supplied facts, explicit uncertainty and expected rendering.','Compare original action label spans and single whole-program edit label spans after dual-tokenizer compilation.'],'positive_credit_if_validated':'New-authored bounded code correction/resource generation A only; no original R, actual historical repair, verified hiring/legal outcome, qualified skill or autonomous pipeline credit.'})
 report={'schema':'wrd-gap08-source-grounded-four-program-correction-proposals-v1','status':'NEW_AUTHORED_PROPOSALS_SYNTAX_CHECKED_NOT_EXECUTED_NOT_ADMITTED','review_source':P(BASE/'THREE_PROGRAM_SEMANTIC_QA02.json'),'programs':entries,'total_programs':4,'total_corrections':sum(x['change_count'] for x in entries),'max_new_whole_program_edit_examples_if_pass':4,'not_13_independent_samples':True,'new_business_Teacher_Actor_or_old_Agent_calls':0,'AI_curation_and_CPU_cost':'UNKNOWN_NOT_ZERO','no_training':True,'script':P(__file__)}
 p=BASE/'SOURCE_GROUNDED_CORRECTION_PROPOSALS.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'report':P(p),'programs':4,'changes':report['total_corrections'],'max_whole_program_edit_targets':4}))

if __name__=='__main__':main()
